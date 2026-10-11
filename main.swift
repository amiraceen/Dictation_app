import Cocoa
import AVFoundation

class AppDelegate: NSObject, NSApplicationDelegate {

    // MARK: - Properties

    private var statusItem: NSStatusItem!
    private var statusMenuItem: NSMenuItem!

    private var isRecording   = false
    private var daemonReady   = false
    private var audioRecorder: AVAudioRecorder?
    private var currentAudioURL: URL?

    private var daemon:   Process?
    private var daemonIn: FileHandle?
    private var lineBuffer = Data()
    private let bufferQueue = DispatchQueue(label: "com.dictation.buffer")

    private var pythonPath: String {
        NSHomeDirectory() + "/Desktop/dictation-app/venv/bin/python3"
    }
    private var daemonScript: String {
        // Use bundled copy if available, else fall back to source folder
        if let rp = Bundle.main.resourcePath {
            let p = (rp as NSString).appendingPathComponent("dictation_daemon.py")
            if FileManager.default.fileExists(atPath: p) { return p }
        }
        return NSHomeDirectory() + "/Desktop/dictation-app/dictation_daemon.py"
    }
    private var snippetsPath: String {
        NSHomeDirectory() + "/Desktop/dictation-app/snippets.json"
    }

    // MARK: - App lifecycle

    func applicationDidFinishLaunching(_ n: Notification) {
        buildMenu()
        launchDaemon()
        setupHotkey()
    }

    func applicationWillTerminate(_ n: Notification) {
        daemon?.terminate()
    }

    // MARK: - Menu bar

    private func buildMenu() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "⏳"

        let menu = NSMenu()

        statusMenuItem = NSMenuItem(title: "Starting…", action: nil, keyEquivalent: "")
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)
        menu.addItem(.separator())

        let edit = NSMenuItem(title: "Edit Snippets", action: #selector(openSnippets), keyEquivalent: "")
        edit.target = self
        menu.addItem(edit)

        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Quit Dictation",
                                action: #selector(NSApplication.terminate(_:)),
                                keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc private func openSnippets() {
        NSWorkspace.shared.open(URL(fileURLWithPath: snippetsPath))
    }

    private func setStatus(_ icon: String, _ msg: String) {
        DispatchQueue.main.async {
            self.statusItem.button?.title = icon
            self.statusMenuItem.title     = msg
        }
    }

    // MARK: - Python daemon

    private func launchDaemon() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: pythonPath)
        p.arguments     = ["-u", daemonScript]          // -u = unbuffered stdout

        let inPipe  = Pipe()
        let outPipe = Pipe()
        p.standardInput  = inPipe
        p.standardOutput = outPipe
        p.standardError  = Pipe()                        // silence stderr

        p.terminationHandler = { [weak self] _ in
            self?.daemonReady = false
            self?.setStatus("❌", "AI process stopped — restarting…")
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { self?.launchDaemon() }
        }

        outPipe.fileHandleForReading.readabilityHandler = { [weak self] fh in
            let chunk = fh.availableData
            guard !chunk.isEmpty else { return }
            self?.bufferQueue.async { self?.consume(chunk) }
        }

        do {
            try p.run()
            daemon   = p
            daemonIn = inPipe.fileHandleForWriting
        } catch {
            setStatus("❌", "Python not found. Run setup.sh first.")
        }
    }

    private func consume(_ chunk: Data) {
        lineBuffer.append(chunk)
        while let idx = lineBuffer.firstIndex(of: UInt8(ascii: "\n")) {
            let slice = lineBuffer[lineBuffer.startIndex ..< idx]
            lineBuffer.removeSubrange(lineBuffer.startIndex ... idx)
            if let line = String(data: slice, encoding: .utf8)?
                .trimmingCharacters(in: .whitespacesAndNewlines), !line.isEmpty {
                handle(line: line)
            }
        }
    }

    private func handle(line: String) {
        if line == "LOADING" {
            setStatus("⏳", "Loading Whisper model… (first run ~30s)")
        } else if line == "READY" {
            daemonReady = true
            setStatus("🎤", "Ready — hold ⌥ Right to dictate")
        } else if line.hasPrefix("TEXT:") {
            let text = String(line.dropFirst(5))
            if text.isEmpty {
                setStatus("🎤", "Ready — hold ⌥ Right to dictate")
            } else {
                DispatchQueue.global(qos: .userInteractive).async { self.typeText(text) }
                let preview = text.count > 50 ? String(text.prefix(50)) + "…" : text
                setStatus("🎤", "✓ \(preview)")
            }
        } else if line.hasPrefix("ERROR:") {
            let msg = String(line.dropFirst(6))
            setStatus("❌", msg)
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                self.setStatus("🎤", "Ready — hold ⌥ Right to dictate")
            }
        }
    }

    private func send(audioPath: String) {
        guard let data = (audioPath + "\n").data(using: .utf8) else { return }
        daemonIn?.write(data)
    }

    // MARK: - Global hotkey (Right Option = keycode 61)

    private func setupHotkey() {
        let mask = CGEventMask(
            (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
        )
        let ref = Unmanaged.passUnretained(self).toOpaque()

        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: mask,
            callback: { _, type, event, ctx -> Unmanaged<CGEvent>? in
                Unmanaged<AppDelegate>
                    .fromOpaque(ctx!)
                    .takeUnretainedValue()
                    .onKey(type: type, event: event)
            },
            userInfo: ref
        ) else {
            setStatus("❌", "Add Dictation to Accessibility in System Settings")
            return
        }

        let src = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), src, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
    }

    private func onKey(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        guard event.getIntegerValueField(.keyboardEventKeycode) == 61 else {
            return Unmanaged.passUnretained(event)
        }
        if type == .keyDown && !isRecording && daemonReady {
            DispatchQueue.main.async { self.startRecording() }
            return nil   // consume — don't pass Right Option to other apps
        }
        if type == .keyUp && isRecording {
            DispatchQueue.main.async { self.stopRecording() }
            return nil
        }
        return Unmanaged.passUnretained(event)
    }

    // MARK: - Recording

    private func startRecording() {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("dictation_\(Int(Date().timeIntervalSince1970)).wav")
        currentAudioURL = url

        let settings: [String: Any] = [
            AVFormatIDKey:            Int(kAudioFormatLinearPCM),
            AVSampleRateKey:          16000.0,
            AVNumberOfChannelsKey:    1,
            AVLinearPCMBitDepthKey:   16,
            AVLinearPCMIsFloatKey:    false,
            AVLinearPCMIsBigEndianKey: false,
        ]

        do {
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            guard audioRecorder?.record() == true else {
                setStatus("❌", "Mic blocked — check Microphone in System Settings")
                return
            }
            isRecording = true
            setStatus("🔴", "Recording…")
        } catch {
            setStatus("❌", "Mic error: \(error.localizedDescription)")
        }
    }

    private func stopRecording() {
        guard isRecording, let url = currentAudioURL else { return }
        audioRecorder?.stop()
        audioRecorder = nil
        isRecording   = false
        setStatus("⚙️", "Transcribing…")
        send(audioPath: url.path)
    }

    // MARK: - Typing (requires Accessibility permission)

    private func typeText(_ text: String) {
        Thread.sleep(forTimeInterval: 0.2)
        for ch in text {
            var u16 = Array(ch.utf16)
            let src = CGEventSource(stateID: .combinedSessionState)
            if let dn = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: true) {
                dn.keyboardSetUnicodeString(stringLength: u16.count, unicodeString: &u16)
                dn.post(tap: .cghidEventTap)
            }
            if let up = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: false) {
                up.keyboardSetUnicodeString(stringLength: u16.count, unicodeString: &u16)
                up.post(tap: .cghidEventTap)
            }
            Thread.sleep(forTimeInterval: 0.004)
        }
    }
}

// MARK: - Entry point
let app      = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)   // no Dock icon
app.run()
