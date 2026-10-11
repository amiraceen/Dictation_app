@import Cocoa;
@import AVFoundation;
@import Speech;
@import CoreMedia;

// ──────────────────────────────────────────────
// MARK: Waveform View
// ──────────────────────────────────────────────

@interface WaveView : NSView
- (void)startIdleWave;
- (void)pushLevel:(float)level;
- (void)resetBars;
@end

@implementation WaveView {
    NSArray<CALayer *> *_bars;
    NSMutableArray<NSNumber *> *_levels;
    NSTimer  *_idleTimer;
    float     _phase;
}

- (instancetype)initWithFrame:(NSRect)f {
    if ((self = [super initWithFrame:f])) {
        self.wantsLayer = YES;
        _levels = [NSMutableArray array];
        for (int i = 0; i < 30; i++) [_levels addObject:@0.0f];
    }
    return self;
}

- (void)layout {
    [super layout];
    if (_bars) return;
    NSMutableArray *tmp = [NSMutableArray array];
    for (int i = 0; i < 30; i++) {
        CALayer *b = [CALayer layer];
        b.backgroundColor = [NSColor.whiteColor colorWithAlphaComponent:0.9].CGColor;
        b.cornerRadius = 2;
        [self.layer addSublayer:b];
        [tmp addObject:b];
    }
    _bars = [tmp copy];
    [self redraw];
}

- (void)startIdleWave {
    _idleTimer = [NSTimer scheduledTimerWithTimeInterval:0.05 repeats:YES block:^(NSTimer *t) {
        self->_phase += 0.20f;
        for (int i = 0; i < 30; i++)
            self->_levels[i] = @(0.10f + 0.08f * sinf(self->_phase + i * 0.40f));
        [self redraw];
    }];
}

- (void)pushLevel:(float)level {
    [_levels removeObjectAtIndex:0];
    [_levels addObject:@(level)];
    dispatch_async(dispatch_get_main_queue(), ^{ [self redraw]; });
}

- (void)resetBars {
    [_idleTimer invalidate]; _idleTimer = nil;
    for (int i = 0; i < 30; i++) _levels[i] = @0.0f;
    [self redraw];
}

- (void)redraw {
    if (!_bars) return;
    CGFloat gap = self.bounds.size.width / 30.0;
    CGFloat bw  = gap * 0.50;
    CGFloat h   = self.bounds.size.height;
    [CATransaction begin];
    [CATransaction setAnimationDuration:0.06];
    for (int i = 0; i < 30; i++) {
        float lv   = [_levels[i] floatValue];
        CGFloat bh = MAX(3, lv * h);
        _bars[i].frame = CGRectMake(i*gap + (gap-bw)/2, (h-bh)/2, bw, bh);
    }
    [CATransaction commit];
}
@end


// ──────────────────────────────────────────────
// MARK: Virtual Keyboard
// ──────────────────────────────────────────────

// Non-activating key button — clicks never steal focus from target app
@interface VKButton : NSButton
@end
@implementation VKButton
- (BOOL)acceptsFirstMouse:(NSEvent *)e { return YES; }
- (BOOL)canBecomeKeyView              { return NO;  }
@end

@interface KeyboardPanel : NSPanel
- (instancetype)initWithTypeBlock:(void(^)(NSString*))typeBlock;
- (void)toggle;
@end

@implementation KeyboardPanel {
    void(^_typeBlock)(NSString *);
    NSView   *_bg;
    BOOL      _shifted;
    BOOL      _arabic;
    NSMutableArray<VKButton*> *_charBtns;
    VKButton *_shiftBtn;
    VKButton *_langBtn;
}

static NSArray* enRows()   { return @[@[@"1",@"2",@"3",@"4",@"5",@"6",@"7",@"8",@"9",@"0"],
                                        @[@"q",@"w",@"e",@"r",@"t",@"y",@"u",@"i",@"o",@"p"],
                                        @[@"a",@"s",@"d",@"f",@"g",@"h",@"j",@"k",@"l"],
                                        @[@"z",@"x",@"c",@"v",@"b",@"n",@"m",@".",@","]]; }
static NSArray* enShift()  { return @[@[@"!",@"@",@"#",@"$",@"%",@"^",@"&",@"*",@"(",@")"],
                                        @[@"Q",@"W",@"E",@"R",@"T",@"Y",@"U",@"I",@"O",@"P"],
                                        @[@"A",@"S",@"D",@"F",@"G",@"H",@"J",@"K",@"L"],
                                        @[@"Z",@"X",@"C",@"V",@"B",@"N",@"M",@">",@"<"]]; }
static NSArray* arRows()   { return @[@[@"1",@"2",@"3",@"4",@"5",@"6",@"7",@"8",@"9",@"0"],
                                        @[@"ض",@"ص",@"ث",@"ق",@"ف",@"غ",@"ع",@"ه",@"خ",@"ح"],
                                        @[@"ش",@"س",@"ي",@"ب",@"ل",@"ا",@"ت",@"ن",@"م"],
                                        @[@"ئ",@"ء",@"ؤ",@"ر",@"ى",@"ة",@"و",@"ز",@"ظ"]]; }

- (instancetype)initWithTypeBlock:(void(^)(NSString*))typeBlock {
    CGFloat W = 470, H = 210;
    NSRect scr = NSScreen.mainScreen.frame;
    self = [super initWithContentRect:NSMakeRect((scr.size.width-W)/2, scr.size.height/4, W, H)
                            styleMask:NSWindowStyleMaskNonactivatingPanel|NSWindowStyleMaskBorderless
                              backing:NSBackingStoreBuffered defer:NO];
    _typeBlock  = [typeBlock copy];
    _charBtns   = [NSMutableArray array];
    self.level  = NSFloatingWindowLevel;
    self.backgroundColor = NSColor.clearColor;
    self.opaque = NO; self.hasShadow = YES;
    self.movableByWindowBackground = YES;
    self.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces
                            | NSWindowCollectionBehaviorFullScreenAuxiliary;

    NSVisualEffectView *bg = [[NSVisualEffectView alloc] initWithFrame:NSMakeRect(0,0,W,H)];
    bg.material = NSVisualEffectMaterialHUDWindow;
    bg.blendingMode = NSVisualEffectBlendingModeBehindWindow;
    bg.state = NSVisualEffectStateActive;
    bg.wantsLayer = YES; bg.layer.cornerRadius = 14; bg.layer.masksToBounds = YES;
    self.contentView = _bg = bg;
    [self buildKeys];
    return self;
}

- (BOOL)canBecomeKeyWindow  { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }

- (void)toggle {
    self.isVisible ? [self orderOut:nil] : [self orderFrontRegardless];
}

// ── Build / rebuild all keys ──────────────────────────────────────

- (void)buildKeys {
    for (NSView *v in _bg.subviews.copy) [v removeFromSuperview];
    [_charBtns removeAllObjects];

    NSArray *rows = _arabic ? arRows() : (_shifted ? enShift() : enRows());
    CGFloat W = self.frame.size.width;
    CGFloat kH = 30, gap = 4, padY = 10;

    // Rows 0-3 (top to bottom on screen = index 3 to 0 in data, but we want
    // row 0 at top so y counts down from top)
    CGFloat rowYs[4];
    rowYs[0] = 210 - padY - kH;            // numbers row
    rowYs[1] = rowYs[0] - kH - gap;
    rowYs[2] = rowYs[1] - kH - gap;
    rowYs[3] = rowYs[2] - kH - gap;

    for (NSInteger r = 0; r < 4; r++) {
        NSArray *chars = rows[r];
        CGFloat kW = 38;

        // Extra special keys per row
        NSInteger extras = 0;
        if (r == 0) extras = 1;  // ⌫
        if (r == 2) extras = 1;  // ↩
        if (r == 3) extras = 2;  // ⇧ ⇧
        CGFloat specialW = 52;

        CGFloat rowW = chars.count * kW + extras * specialW + (chars.count + extras - 1) * gap;
        CGFloat x = (W - rowW) / 2.0;
        CGFloat y = rowYs[r];

        if (r == 3) { // leading ⇧
            [self addSpecial:@"⇧" x:x y:y w:specialW h:kH action:@selector(shiftTap:) highlight:_shifted];
            _shiftBtn = (VKButton *)_bg.subviews.lastObject;
            x += specialW + gap;
        }

        for (NSString *ch in chars) {
            VKButton *b = [self key:ch w:kW h:kH];
            b.frame = NSMakeRect(x, y, kW, kH);
            NSString *cap = ch; __weak KeyboardPanel *ws = self;
            b.target = self;
            b.action = @selector(charTap:);
            b.identifier = cap;
            [_charBtns addObject:b];
            [_bg addSubview:b];
            x += kW + gap;
        }

        if (r == 0) [self addSpecial:@"⌫" x:x y:y w:specialW h:kH action:@selector(backTap:) highlight:NO];
        if (r == 2) [self addSpecial:@"↩" x:x y:y w:specialW h:kH action:@selector(retTap:)  highlight:NO];
        if (r == 3) [self addSpecial:@"⇧" x:x y:y w:specialW h:kH action:@selector(shiftTap:) highlight:_shifted];
    }

    // Bottom row: Space · Lang · ✕
    CGFloat by = padY;
    CGFloat spW = 200, lgW = 64, clW = 46;
    CGFloat totalBW = spW + lgW + clW + 2*gap;
    CGFloat bx = (W - totalBW) / 2.0;

    [self addSpecial:@"space" x:bx y:by w:spW h:kH action:@selector(spaceTap:) highlight:NO];
    bx += spW + gap;
    VKButton *lg = [self key:(_arabic ? @"EN" : @"عر") w:lgW h:kH];
    lg.frame = NSMakeRect(bx, by, lgW, kH);
    lg.layer.backgroundColor = [NSColor colorWithRed:0.2 green:0.4 blue:0.8 alpha:0.9].CGColor;
    [lg setTarget:self]; [lg setAction:@selector(langTap:)];
    _langBtn = lg; [_bg addSubview:lg];
    bx += lgW + gap;
    VKButton *cl = [self key:@"✕" w:clW h:kH];
    cl.frame = NSMakeRect(bx, by, clW, kH);
    cl.layer.backgroundColor = [NSColor colorWithRed:0.75 green:0.18 blue:0.18 alpha:0.9].CGColor;
    [cl setTarget:self]; [cl setAction:@selector(closeTap:)];
    [_bg addSubview:cl];
}

- (VKButton *)key:(NSString *)title w:(CGFloat)w h:(CGFloat)h {
    VKButton *b = [[VKButton alloc] initWithFrame:NSMakeRect(0,0,w,h)];
    b.title = title; b.bordered = NO;
    b.font = [NSFont systemFontOfSize:13 weight:NSFontWeightMedium];
    b.contentTintColor = NSColor.whiteColor;
    b.wantsLayer = YES; b.layer.cornerRadius = 5;
    b.layer.backgroundColor = [NSColor colorWithWhite:0.22 alpha:0.95].CGColor;
    return b;
}

- (void)addSpecial:(NSString *)t x:(CGFloat)x y:(CGFloat)y w:(CGFloat)w h:(CGFloat)h
            action:(SEL)action highlight:(BOOL)hi {
    VKButton *b = [self key:t w:w h:h];
    b.frame = NSMakeRect(x, y, w, h);
    if (hi) b.layer.backgroundColor = [NSColor colorWithRed:0.3 green:0.55 blue:1.0 alpha:0.9].CGColor;
    [b setTarget:self]; [b setAction:action];
    [_bg addSubview:b];
}

// ── Key actions ───────────────────────────────────────────────────

- (void)charTap:(VKButton *)b {
    if (_typeBlock) _typeBlock(b.identifier);
    // Auto-release shift after one char (English)
    if (_shifted && !_arabic) { _shifted = NO; [self buildKeys]; }
}

- (void)shiftTap:(id)_ { _shifted = !_shifted; [self buildKeys]; }
- (void)langTap:(id)_  { _arabic  = !_arabic;  _shifted = NO; [self buildKeys]; }
- (void)spaceTap:(id)_ { if (_typeBlock) _typeBlock(@" "); }
- (void)closeTap:(id)_ { [self orderOut:nil]; }

- (void)backTap:(id)_ {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE,0), ^{
        CGEventSourceRef s = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState);
        CGEventRef d = CGEventCreateKeyboardEvent(s,51,true);
        CGEventPost(kCGHIDEventTap,d); CFRelease(d);
        CGEventRef u = CGEventCreateKeyboardEvent(s,51,false);
        CGEventPost(kCGHIDEventTap,u); CFRelease(u); CFRelease(s);
    });
}

- (void)retTap:(id)_ {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE,0), ^{
        CGEventSourceRef s = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState);
        CGEventRef d = CGEventCreateKeyboardEvent(s,36,true);
        CGEventPost(kCGHIDEventTap,d); CFRelease(d);
        CGEventRef u = CGEventCreateKeyboardEvent(s,36,false);
        CGEventPost(kCGHIDEventTap,u); CFRelease(u); CFRelease(s);
    });
}

@end


// ──────────────────────────────────────────────
// MARK: Overlay Panel
// ──────────────────────────────────────────────

@interface OverlayPanel : NSPanel
@property (nonatomic, strong) WaveView *wave;
- (void)showBar;
- (void)hideBarWithCompletion:(void(^)(void))done;
@end

@implementation OverlayPanel

- (instancetype)init {
    CGFloat W = 170, H = 28;
    NSRect scr = NSScreen.mainScreen.frame;
    NSRect r = NSMakeRect((scr.size.width - W) / 2.0, 60, W, H);
    self = [super initWithContentRect:r
                            styleMask:NSWindowStyleMaskNonactivatingPanel
                                      | NSWindowStyleMaskBorderless
                              backing:NSBackingStoreBuffered
                                defer:NO];
    self.level = NSScreenSaverWindowLevel;
    self.backgroundColor   = NSColor.clearColor;
    self.opaque            = NO;
    self.hasShadow         = YES;
    self.alphaValue        = 0.45;
    self.movableByWindowBackground = YES;
    self.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces
                            | NSWindowCollectionBehaviorFullScreenAuxiliary;

    NSVisualEffectView *fx = [[NSVisualEffectView alloc] initWithFrame:NSMakeRect(0,0,W,H)];
    fx.material       = NSVisualEffectMaterialHUDWindow;
    fx.blendingMode   = NSVisualEffectBlendingModeBehindWindow;
    fx.state          = NSVisualEffectStateActive;
    fx.wantsLayer     = YES;
    fx.layer.cornerRadius   = H / 2;
    fx.layer.masksToBounds  = YES;

    NSTextField *dot = [NSTextField labelWithString:@"⏺"];
    dot.frame     = NSMakeRect(10, (H-18)/2, 18, 18);
    dot.font      = [NSFont systemFontOfSize:11];
    dot.textColor = [NSColor colorWithRed:1 green:0.25 blue:0.25 alpha:1];
    [fx addSubview:dot];

    _wave = [[WaveView alloc] initWithFrame:NSMakeRect(32, 6, W-40, H-12)];
    [fx addSubview:_wave];
    self.contentView = fx;
    return self;
}

- (BOOL)canBecomeKeyWindow  { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }

- (void)showBar {
    self.alphaValue = 0;
    [self orderFrontRegardless];
    [NSAnimationContext runAnimationGroup:^(NSAnimationContext *c) {
        c.duration = 0.15;
        self.animator.alphaValue = 1;
    }];
    [_wave startIdleWave];
}

- (void)hideBarWithCompletion:(void(^)(void))done {
    [_wave resetBars];
    [NSAnimationContext runAnimationGroup:^(NSAnimationContext *c) {
        c.duration = 0.15;
        self.animator.alphaValue = 0;
    } completionHandler:^{
        [self orderOut:nil];
        self.alphaValue = 1;
        if (done) done();
    }];
}
@end


// ──────────────────────────────────────────────
// MARK: CGEventTap C callback
// ──────────────────────────────────────────────

static CGEventRef tapCallback(CGEventTapProxy proxy,
                               CGEventType    type,
                               CGEventRef     event,
                               void          *ref);


// ──────────────────────────────────────────────
// MARK: App Delegate
// ──────────────────────────────────────────────

@interface AppDelegate : NSObject <NSApplicationDelegate, AVCaptureAudioDataOutputSampleBufferDelegate>
- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event;
@end

@implementation AppDelegate {
    NSStatusItem              *_statusItem;
    OverlayPanel              *_overlay;
    CFMachPortRef              _tap;
    BOOL                       _recording;
    NSString                  *_currentLanguage;

    // Audio capture — uses explicit built-in mic, immune to Bluetooth
    AVCaptureSession          *_captureSession;
    AVCaptureAudioDataOutput  *_captureOutput;

    SFSpeechRecognizer                     *_recognizer;
    SFSpeechAudioBufferRecognitionRequest  *_request;
    SFSpeechRecognitionTask                *_task;
    NSString                               *_partial;
    BOOL                                    _typed;   // prevents double-type from isFinal + timeout

    NSMutableDictionary<NSString*,NSString*> *_corrections;
    NSMutableArray<NSString*>               *_customWords;
    KeyboardPanel                           *_keyboard;
}

- (void)applicationDidFinishLaunching:(NSNotification *)n {
    _partial         = @"";
    _currentLanguage = @"en-US";
    _corrections     = [NSMutableDictionary dictionary];
    _customWords     = [NSMutableArray array];
    [self loadDictionary];
    [self buildStatusBar];
    [self requestPermissions];
}

- (void)buildStatusBar {
    _statusItem = [NSStatusBar.systemStatusBar
                   statusItemWithLength:NSVariableStatusItemLength];
    _statusItem.button.title = @"✦";

    NSMenu *m = [NSMenu new];
    NSMenuItem *tip = [[NSMenuItem alloc]
                       initWithTitle:@"Hold Right ⇧ Shift to dictate"
                              action:nil keyEquivalent:@""];
    tip.enabled = NO;
    [m addItem:tip];
    [m addItem:NSMenuItem.separatorItem];

    NSMenuItem *langMenu = [[NSMenuItem alloc] initWithTitle:@"Language" action:nil keyEquivalent:@""];
    NSMenu *langs = [NSMenu new];
    NSMenuItem *en = [[NSMenuItem alloc] initWithTitle:@"🇬🇧 English" action:@selector(setEnglish:) keyEquivalent:@""];
    NSMenuItem *ar = [[NSMenuItem alloc] initWithTitle:@"🇸🇦 Arabic"  action:@selector(setArabic:)  keyEquivalent:@""];
    en.state = NSControlStateValueOn;
    [langs addItem:en]; [langs addItem:ar];
    langMenu.submenu = langs;
    [m addItem:langMenu];
    [m addItem:NSMenuItem.separatorItem];

    NSMenuItem *dictMenu = [[NSMenuItem alloc] initWithTitle:@"My Dictionary" action:nil keyEquivalent:@""];
    NSMenu *dict = [NSMenu new];
    [dict addItem:[[NSMenuItem alloc] initWithTitle:@"Add Word or Name…"  action:@selector(addWord:)        keyEquivalent:@""]];
    [dict addItem:[[NSMenuItem alloc] initWithTitle:@"Add Correction…"    action:@selector(addCorrection:)  keyEquivalent:@""]];
    [dict addItem:NSMenuItem.separatorItem];
    [dict addItem:[[NSMenuItem alloc] initWithTitle:@"View Dictionary"    action:@selector(viewDictionary:) keyEquivalent:@""]];
    dictMenu.submenu = dict;
    [m addItem:dictMenu];
    [m addItem:NSMenuItem.separatorItem];

    [m addItem:[[NSMenuItem alloc] initWithTitle:@"Show Keyboard"
                                         action:@selector(toggleKeyboard:)
                                  keyEquivalent:@"k"]];
    [m addItem:NSMenuItem.separatorItem];
    [m addItem:[[NSMenuItem alloc] initWithTitle:@"Quit"
                                         action:@selector(terminate:)
                                  keyEquivalent:@"q"]];
    _statusItem.menu = m;
}

- (void)toggleKeyboard:(NSMenuItem *)item {
    if (!_keyboard) {
        __weak typeof(self) ws = self;
        _keyboard = [[KeyboardPanel alloc] initWithTypeBlock:^(NSString *ch) {
            dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE,0), ^{
                [ws typeChar:ch];   // keyboard uses direct key events (not paste)
            });
        }];
    }
    [_keyboard toggle];
    item.title = _keyboard.isVisible ? @"Hide Keyboard" : @"Show Keyboard";
}

- (void)setEnglish:(NSMenuItem *)item { [self switchLanguage:@"en-US" menuItem:item]; }
- (void)setArabic:(NSMenuItem *)item  { [self switchLanguage:@"ar-SA" menuItem:item]; }

- (void)switchLanguage:(NSString *)lang menuItem:(NSMenuItem *)item {
    for (NSMenuItem *i in item.menu.itemArray) i.state = NSControlStateValueOff;
    item.state = NSControlStateValueOn;
    _currentLanguage = lang;
    _recognizer = [[SFSpeechRecognizer alloc] initWithLocale:[NSLocale localeWithLocaleIdentifier:lang]];
}

- (void)setIcon:(NSString *)s {
    dispatch_async(dispatch_get_main_queue(), ^{ self->_statusItem.button.title = s; });
}

// ── Permissions ──────────────────────────────────────────────────

- (void)requestPermissions {
    [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio completionHandler:^(BOOL g){}];
    [SFSpeechRecognizer requestAuthorization:^(SFSpeechRecognizerAuthorizationStatus st) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (st == SFSpeechRecognizerAuthorizationStatusAuthorized) {
                self->_recognizer = [[SFSpeechRecognizer alloc] initWithLocale:[NSLocale localeWithLocaleIdentifier:@"en-US"]];
                [self attemptSetupTap];
            } else {
                [self setIcon:@"❌"];
            }
        });
    }];
}

// ── Accessibility auto-retry ──────────────────────────────────────

- (void)attemptSetupTap {
    static BOOL _prompted = NO;
    BOOL trusted;
    if (!_prompted) {
        _prompted = YES;
        NSDictionary *opts = @{(__bridge id)kAXTrustedCheckOptionPrompt: @YES};
        trusted = AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)opts);
    } else {
        trusted = AXIsProcessTrusted();
    }
    if (!trusted) {
        [self setIcon:@"⚠️"];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC),
                       dispatch_get_main_queue(), ^{ [self attemptSetupTap]; });
        return;
    }
    [self createTap];
}

- (void)createTap {
    CGEventMask mask = CGEventMaskBit(kCGEventFlagsChanged);
    _tap = CGEventTapCreate(kCGSessionEventTap,
                            kCGHeadInsertEventTap,
                            kCGEventTapOptionDefault,
                            mask,
                            tapCallback,
                            (__bridge void *)self);
    if (_tap) {
        CFRunLoopSourceRef src = CFMachPortCreateRunLoopSource(nil, _tap, 0);
        CFRunLoopAddSource(CFRunLoopGetMain(), src, kCFRunLoopCommonModes);
        CGEventTapEnable(_tap, true);
        CFRelease(src);
        [self setIcon:@"✦"];
    } else {
        [self setIcon:@"❌"];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC),
                       dispatch_get_main_queue(), ^{ [self attemptSetupTap]; });
    }
}

// ── Key handler ───────────────────────────────────────────────────

- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event {
    int64_t kc = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);
    if (type != kCGEventFlagsChanged || kc != 60)
        return event;
    BOOL down = (CGEventGetFlags(event) & kCGEventFlagMaskShift) != 0;
    if (down && !_recording)
        dispatch_async(dispatch_get_main_queue(), ^{ [self startRecording]; });
    else if (!down && _recording)
        dispatch_async(dispatch_get_main_queue(), ^{ [self stopRecording]; });
    return NULL;
}

// ── Find built-in mic via AVCaptureDevice ─────────────────────────

- (AVCaptureDevice *)builtInMic {
    // 1. Try the explicit built-in type (most reliable when available)
    AVCaptureDevice *d = [AVCaptureDevice
        defaultDeviceWithDeviceType:AVCaptureDeviceTypeBuiltInMicrophone
                          mediaType:AVMediaTypeAudio
                           position:AVCaptureDevicePositionUnspecified];
    if (d) return d;

    // 2. Search by name — actively skip Bluetooth / headphone / AirPods mics
    //    (those mics pick up music playing through the earphones)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    NSArray<AVCaptureDevice *> *all = [AVCaptureDevice devicesWithMediaType:AVMediaTypeAudio];
    for (AVCaptureDevice *dev in all) {
        NSString *name = dev.localizedName.lowercaseString;
        if ([name containsString:@"bluetooth"] || [name containsString:@"airpod"] ||
            [name containsString:@"headphone"] || [name containsString:@"headset"] ||
            [name containsString:@"wireless"])
            continue;   // skip Bluetooth devices
        if ([name containsString:@"built-in"] || [name containsString:@"built in"] ||
            [name containsString:@"macbook"]  || [name containsString:@"internal"] ||
            [name containsString:@"microphone"])
            return dev;
    }
    // 3. Last resort: first non-Bluetooth device
    for (AVCaptureDevice *dev in all) {
        NSString *name = dev.localizedName.lowercaseString;
        if (![name containsString:@"bluetooth"] && ![name containsString:@"airpod"] &&
            ![name containsString:@"headphone"] && ![name containsString:@"headset"] &&
            ![name containsString:@"wireless"])
            return dev;
    }
    return [AVCaptureDevice defaultDeviceWithMediaType:AVMediaTypeAudio];
#pragma clang diagnostic pop
}

// ── Recording ─────────────────────────────────────────────────────

- (void)startRecording {
    if (!_recognizer.isAvailable) { [self setIcon:@"❌"]; return; }

    // Cancel any leftover task from a previous session before starting fresh
    [_task cancel];      _task    = nil;
    [_request endAudio]; _request = nil;

    _recording = YES;
    _typed     = NO;
    _partial   = @"";

    [[NSSound soundNamed:@"Tink"] play];
    [self setIcon:@"🔴"];
    if (!_overlay) _overlay = [OverlayPanel new];
    [_overlay showBar];

    // ── Recognition request ──
    SFSpeechAudioBufferRecognitionRequest *req = [SFSpeechAudioBufferRecognitionRequest new];
    req.shouldReportPartialResults = YES;
    if (@available(macOS 13, *)) req.addsPunctuation = YES;
    if (_customWords.count > 0) req.contextualStrings = _customWords;
    _request = req;

    // ── AVCaptureSession with explicit built-in mic ──
    // Bypasses Bluetooth audio routing — headphone mics are skipped
    _captureSession = [AVCaptureSession new];
    AVCaptureDevice *mic = [self builtInMic];
    NSError *capErr = nil;
    AVCaptureDeviceInput *capInput = [AVCaptureDeviceInput deviceInputWithDevice:mic error:&capErr];
    if (capInput && [_captureSession canAddInput:capInput])
        [_captureSession addInput:capInput];

    _captureOutput = [AVCaptureAudioDataOutput new];
    dispatch_queue_t audioQ = dispatch_queue_create("com.dictation.audio", DISPATCH_QUEUE_SERIAL);
    [_captureOutput setSampleBufferDelegate:self queue:audioQ];
    if ([_captureSession canAddOutput:_captureOutput])
        [_captureSession addOutput:_captureOutput];

    [[NSNotificationCenter defaultCenter]
        addObserver:self selector:@selector(captureSessionError:)
               name:AVCaptureSessionRuntimeErrorNotification object:_captureSession];
    [[NSNotificationCenter defaultCenter]
        addObserver:self selector:@selector(captureSessionInterrupted:)
               name:AVCaptureSessionWasInterruptedNotification object:_captureSession];

    [_captureSession startRunning];

    // ── Recognition task ──
    // Result handler always dispatched to main queue for thread safety
    __weak typeof(self) ws = self;
    _task = [_recognizer recognitionTaskWithRequest:req
             resultHandler:^(SFSpeechRecognitionResult *r, NSError *e) {
        dispatch_async(dispatch_get_main_queue(), ^{
            __strong typeof(ws) ss = ws; if (!ss) return;

            if (r) ss->_partial = r.bestTranscription.formattedString;

            // Type when we get a final result, OR when we get an error after
            // recording has already stopped (network error = use partial)
            BOOL shouldType = (r.isFinal || (e && !ss->_recording))
                              && !ss->_recording
                              && !ss->_typed
                              && ss->_partial.length > 0;
            if (shouldType) {
                ss->_typed = YES;
                [ss->_task cancel]; ss->_task = nil; ss->_request = nil;
                [ss setIcon:@"✦"];
                NSString *corrected = [ss applyCorrections:ss->_partial];
                [ss typeText:corrected];   // clipboard paste — fast & reliable
            }
        });
    }];
}

- (void)captureSessionError:(NSNotification *)note {
    // Session errored (e.g. audio device changed) — stop gracefully, don't crash
    dispatch_async(dispatch_get_main_queue(), ^{
        if (self->_recording) [self stopRecording];
    });
}

- (void)captureSessionInterrupted:(NSNotification *)note {
    dispatch_async(dispatch_get_main_queue(), ^{
        if (self->_recording) [self stopRecording];
    });
}

- (void)stopRecording {
    if (!_recording) return;
    _recording = NO;

    // Nil delegate FIRST — stops any in-flight callbacks before we release the session
    [_captureOutput setSampleBufferDelegate:nil queue:nil];
    _captureOutput = nil;

    [[NSNotificationCenter defaultCenter] removeObserver:self
        name:AVCaptureSessionRuntimeErrorNotification object:_captureSession];
    [[NSNotificationCenter defaultCenter] removeObserver:self
        name:AVCaptureSessionWasInterruptedNotification object:_captureSession];

    [_captureSession stopRunning];
    _captureSession = nil;
    [_request endAudio];

    [[NSSound soundNamed:@"Pop"] play];
    [_overlay hideBarWithCompletion:nil];
    [self setIcon:@"⚙️"];

    // Safety timeout — fires if isFinal never arrives (e.g. network slow)
    // Uses _typed flag instead of icon title so there's no double-type race
    __weak typeof(self) ws = self;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 4 * NSEC_PER_SEC),
                   dispatch_get_main_queue(), ^{
        __strong typeof(ws) ss = ws;
        if (!ss || ss->_typed) return;   // already typed — do nothing
        ss->_typed = YES;
        [ss->_task cancel]; ss->_task = nil; ss->_request = nil;
        [ss setIcon:@"✦"];
        NSString *text = ss->_partial;
        if (text.length > 0) {
            NSString *corrected = [ss applyCorrections:text];
            [ss typeText:corrected];
        }
    });
}

// ── AVCaptureAudioDataOutputSampleBufferDelegate ──────────────────

- (void)captureOutput:(AVCaptureOutput *)output
didOutputSampleBuffer:(CMSampleBufferRef)sampleBuffer
       fromConnection:(AVCaptureConnection *)connection {

    // Guard: stop processing if recording was cancelled
    if (!_recording || !_request) return;

    CMFormatDescriptionRef fmt = CMSampleBufferGetFormatDescription(sampleBuffer);
    const AudioStreamBasicDescription *asbd = CMAudioFormatDescriptionGetStreamBasicDescription(fmt);
    if (!asbd) return;

    AVAudioFormat *format = [[AVAudioFormat alloc] initWithStreamDescription:asbd];
    CMItemCount frameCount = CMSampleBufferGetNumSamples(sampleBuffer);
    if (frameCount <= 0) return;

    AVAudioPCMBuffer *pcm = [[AVAudioPCMBuffer alloc] initWithPCMFormat:format
                                                          frameCapacity:(AVAudioFrameCount)frameCount];
    if (!pcm) return;
    pcm.frameLength = (AVAudioFrameCount)frameCount;

    CMBlockBufferRef block = CMSampleBufferGetDataBuffer(sampleBuffer);
    size_t totalLen; char *dataPtr;
    CMBlockBufferGetDataPointer(block, 0, NULL, &totalLen, &dataPtr);

    AudioBufferList *abl = pcm.mutableAudioBufferList;
    if (format.interleaved) {
        memcpy(abl->mBuffers[0].mData, dataPtr,
               MIN(totalLen, abl->mBuffers[0].mDataByteSize));
    } else {
        size_t chSize = totalLen / MAX(1, format.channelCount);
        for (uint32_t ch = 0; ch < abl->mNumberBuffers; ch++)
            memcpy(abl->mBuffers[ch].mData, dataPtr + ch * chSize,
                   MIN(chSize, abl->mBuffers[ch].mDataByteSize));
    }

    [_request appendAudioPCMBuffer:pcm];

    // Audio level for waveform
    if (pcm.floatChannelData) {
        float *data = pcm.floatChannelData[0];
        float peak = 0;
        for (AVAudioFrameCount i = 0; i < pcm.frameLength; i++) {
            float v = fabsf(data[i]);
            if (v > peak) peak = v;
        }
        [_overlay.wave pushLevel:fminf(peak * 10.0f, 1.0f)];
    }
}

// ── Type text via clipboard paste (dictation) ─────────────────────
// Uses Cmd+V — instant, reliable, works with Arabic & long texts.
// Old per-character CGEvent approach dropped characters at speed.

- (void)typeText:(NSString *)text {
    if (text.length == 0) return;
    // Must run on main thread (NSPasteboard is not thread-safe)
    dispatch_async(dispatch_get_main_queue(), ^{
        NSPasteboard *pb = NSPasteboard.generalPasteboard;
        // Save whatever the user had in the clipboard
        NSString *saved = [pb stringForType:NSPasteboardTypeString];

        [pb clearContents];
        [pb setString:text forType:NSPasteboardTypeString];

        // Brief pause so the overlay finishes hiding and the target app
        // regains keyboard focus before we send Cmd+V
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.12 * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{
            // keycode 9 = V key on every keyboard layout
            CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState);
            CGEventRef dn = CGEventCreateKeyboardEvent(src, (CGKeyCode)9, true);
            CGEventSetFlags(dn, kCGEventFlagMaskCommand);
            CGEventPost(kCGHIDEventTap, dn); CFRelease(dn);
            CGEventRef up = CGEventCreateKeyboardEvent(src, (CGKeyCode)9, false);
            CGEventSetFlags(up, 0);
            CGEventPost(kCGHIDEventTap, up); CFRelease(up);
            CFRelease(src);

            // Restore the old clipboard content ~0.7 s later
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.7 * NSEC_PER_SEC)),
                           dispatch_get_main_queue(), ^{
                [pb clearContents];
                if (saved) [pb setString:saved forType:NSPasteboardTypeString];
            });
        });
    });
}

// ── Type individual characters (virtual keyboard) ─────────────────
// One character at a time via Unicode key events — correct for a keyboard.

- (void)typeChar:(NSString *)text {
    if (text.length == 0) return;
    CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState);
    for (NSUInteger i = 0; i < text.length; ) {
        unichar c = [text characterAtIndex:i];
        UniChar uc[2]; NSUInteger cnt = 1;
        if (CFStringIsSurrogateHighCharacter(c) && i+1 < text.length) {
            uc[0] = c; uc[1] = [text characterAtIndex:i+1]; cnt = 2; i += 2;
        } else { uc[0] = c; i++; }
        CGEventRef dn = CGEventCreateKeyboardEvent(src, 0, true);
        CGEventKeyboardSetUnicodeString(dn, cnt, uc);
        CGEventPost(kCGHIDEventTap, dn);
        CGEventRef up = CGEventCreateKeyboardEvent(src, 0, false);
        CGEventKeyboardSetUnicodeString(up, cnt, uc);
        CGEventPost(kCGHIDEventTap, up);
        CFRelease(dn); CFRelease(up);
        [NSThread sleepForTimeInterval:0.004];
    }
    CFRelease(src);
}

// ── Personal Dictionary ───────────────────────────────────────────

- (NSString *)dictPath {
    return [@"~/Documents/dictation-app/personal_dict.json" stringByExpandingTildeInPath];
}

- (void)loadDictionary {
    NSData *data = [NSData dataWithContentsOfFile:self.dictPath];
    if (!data) return;
    NSDictionary *d = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    if (d[@"corrections"]) _corrections = [d[@"corrections"] mutableCopy];
    if (d[@"words"])       _customWords = [d[@"words"] mutableCopy];
}

- (void)saveDictionary {
    NSDictionary *d = @{@"corrections": _corrections, @"words": _customWords};
    NSData *data = [NSJSONSerialization dataWithJSONObject:d options:NSJSONWritingPrettyPrinted error:nil];
    [data writeToFile:self.dictPath atomically:YES];
}

- (NSString *)applyCorrections:(NSString *)text {
    if (_corrections.count == 0) return text;
    NSMutableString *r = [text mutableCopy];
    NSArray *keys = [_corrections.allKeys sortedArrayUsingComparator:^(NSString *a, NSString *b){
        return [@(b.length) compare:@(a.length)];
    }];
    for (NSString *from in keys) {
        NSString *to = _corrections[from];
        NSRange range;
        while ((range = [r rangeOfString:from options:NSCaseInsensitiveSearch]).location != NSNotFound)
            [r replaceCharactersInRange:range withString:to];
    }
    return [r copy];
}

- (void)addWord:(id)sender {
    NSAlert *alert = [NSAlert new];
    alert.messageText     = @"Add Word or Name";
    alert.informativeText = @"Enter a word, name, or phrase you use often.";
    [alert addButtonWithTitle:@"Save"]; [alert addButtonWithTitle:@"Cancel"];
    NSTextField *f = [[NSTextField alloc] initWithFrame:NSMakeRect(0,0,300,24)];
    f.placeholderString = @"e.g.  Amira,  MacBook,  Claude AI";
    alert.accessoryView = f;
    if ([alert runModal] == NSAlertFirstButtonReturn) {
        NSString *w = [f.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        if (w.length > 0 && ![_customWords containsObject:w]) {
            [_customWords addObject:w]; [self saveDictionary];
        }
    }
}

- (void)addCorrection:(id)sender {
    NSAlert *alert = [NSAlert new];
    alert.messageText     = @"Add Correction";
    alert.informativeText = @"App hears…  →  type this instead:";
    [alert addButtonWithTitle:@"Save"]; [alert addButtonWithTitle:@"Cancel"];
    NSView *box = [[NSView alloc] initWithFrame:NSMakeRect(0,0,320,58)];
    NSTextField *lbl1 = [NSTextField labelWithString:@"App hears:"];
    lbl1.frame = NSMakeRect(0,36,90,20);
    NSTextField *f1 = [[NSTextField alloc] initWithFrame:NSMakeRect(96,33,224,24)];
    f1.placeholderString = @"e.g.  there";
    NSTextField *lbl2 = [NSTextField labelWithString:@"Type instead:"];
    lbl2.frame = NSMakeRect(0,4,90,20);
    NSTextField *f2 = [[NSTextField alloc] initWithFrame:NSMakeRect(96,1,224,24)];
    f2.placeholderString = @"e.g.  their";
    [box addSubview:lbl1]; [box addSubview:f1]; [box addSubview:lbl2]; [box addSubview:f2];
    alert.accessoryView = box;
    if ([alert runModal] == NSAlertFirstButtonReturn) {
        NSString *from = [f1.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet].lowercaseString;
        NSString *to   = [f2.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        if (from.length > 0 && to.length > 0) {
            _corrections[from] = to; [self saveDictionary];
        }
    }
}

- (void)viewDictionary:(id)sender {
    [[NSWorkspace sharedWorkspace] openFile:self.dictPath withApplication:@"TextEdit"];
}

@end


// ── C callback ────────────────────────────────────────────────────

static CGEventRef tapCallback(CGEventTapProxy proxy,
                               CGEventType    type,
                               CGEventRef     event,
                               void          *ref) {
    return [(__bridge AppDelegate *)ref handleType:type event:event];
}


// ── Entry point ───────────────────────────────────────────────────

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        AppDelegate   *del = [AppDelegate new];
        app.delegate       = del;
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app run];
    }
}
