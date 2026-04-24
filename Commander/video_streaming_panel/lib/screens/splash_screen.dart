
import 'dart:ui';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'drone_control_page.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({Key? key}) : super(key: key);

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with TickerProviderStateMixin {
  late AnimationController _logoController;
  late AnimationController _crossController;

  late Animation<double> _logoScale;
  late Animation<double> _logoOpacity;
  late Animation<double> _underlineProgress;
  late Animation<double> _dot1Opacity;
  late Animation<double> _dot2Opacity;
  late Animation<double> _dot3Opacity;
  late Animation<double> _secondScale;
  late Animation<double> _crossFade;

  bool _showSecond = false;

  @override
  void initState() {
    super.initState();

    _logoController = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));
    _crossController = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));

    _logoScale = Tween<double>(begin: 0.9, end: 1.02).animate(CurvedAnimation(parent: _logoController, curve: Curves.easeOutBack));
    _logoOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _logoController, curve: Curves.easeIn));

    // underline draws after logo shows; dots animate sequentially
    _underlineProgress = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _logoController, curve: const Interval(0.35, 1.0, curve: Curves.easeOut))
    );

    _dot1Opacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _logoController, curve: const Interval(0.6, 0.72, curve: Curves.easeIn)));
    _dot2Opacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _logoController, curve: const Interval(0.72, 0.84, curve: Curves.easeIn)));
    _dot3Opacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _logoController, curve: const Interval(0.84, 0.96, curve: Curves.easeIn)));

    _secondScale = Tween<double>(begin: 0.96, end: 1.0).animate(CurvedAnimation(parent: _crossController, curve: Curves.easeOut));
    _crossFade = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _crossController, curve: Curves.easeInOut));

    _startSequence();
  }

  Future<void> _startSequence() async {
    await Future.delayed(const Duration(milliseconds: 200));
    _logoController.forward();
    await Future.delayed(const Duration(milliseconds: 1600));
    // soft crossfade to second mark
    setState(() => _showSecond = true);
    _crossController.forward();
    await Future.delayed(const Duration(milliseconds: 1600));
    // navigate
    if (!mounted) return;
    Navigator.of(context).pushReplacement(PageRouteBuilder(
      pageBuilder: (context, a1, a2) => const DroneControlPage(),
      transitionsBuilder: (context, anim, sec, child) => FadeTransition(opacity: anim, child: child),
      transitionDuration: const Duration(milliseconds: 900),
    ));
  }

  @override
  void dispose() {
    _logoController.dispose();
    _crossController.dispose();
    super.dispose();
  }

  Widget _monoImage(String asset, double scale, double opacity, double maxSize) {
    return Opacity(
      opacity: opacity,
      child: Transform.scale(
        scale: scale,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxSize, maxHeight: maxSize),
          child: ColorFiltered(
            colorFilter: const ColorFilter.matrix(<double>[
              0.2126, 0.7152, 0.0722, 0, 0,
              0.2126, 0.7152, 0.0722, 0, 0,
              0.2126, 0.7152, 0.0722, 0, 0,
              0, 0, 0, 1, 0,
            ]),
            child: Image.asset(asset, fit: BoxFit.contain),
          ),
        ),
      ),
    );
  }

  Widget _dotWidget() {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        color: Colors.white70,
        shape: BoxShape.circle,
        boxShadow: [BoxShadow(color: Colors.white12, blurRadius: 6, spreadRadius: 1)],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final maxLogo = math.min(size.width, size.height) * 0.45;

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // subtle vignette
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.center,
                  radius: 0.9,
                  colors: [Colors.black, Colors.black87],
                ),
              ),
            ),
          ),

          // center content
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedBuilder(
                  animation: Listenable.merge([_logoController, _crossController]),
                  builder: (context, _) {
                    final firstVisible = !_showSecond ? 1.0 : (1.0 - _crossFade.value);
                    final secondVisible = _showSecond ? _crossFade.value : 0.0;
                    return Stack(
                      alignment: Alignment.center,
                      children: [
                        // first logo (monochrome)
                        _monoImage('assets/images/IOTROCOP.jpeg', _logoScale.value, _logoOpacity.value * firstVisible, maxLogo),
                        // second logo slightly smaller, appears via crossfade
                        _monoImage('assets/images/KTVTurkiye.png', _secondScale.value, secondVisible, maxLogo * 1.1),
                      ],
                    );
                  },
                ),

                const SizedBox(height: 28),
                // App name with animated underline + sequential dots
                AnimatedBuilder(
                  animation: Listenable.merge([_logoController, _crossController]),
                  builder: (context, _) {
                    final visible = _logoOpacity.value;
                    final underline = _underlineProgress.value;
                    return Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // welcome text (Turkish) — remain visible when second logo appears
                        Opacity(
                          opacity: math.max(_logoOpacity.value, _crossFade.value),
                          child: Text(
                            'Hoşgeldiniz',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.98),
                              fontSize: 22,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.8,
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        // animated underline
                        SizedBox(
                          width: maxLogo * 0.5,
                          height: 6,
                          child: Stack(
                            alignment: Alignment.centerLeft,
                            children: [
                              Container(height: 2, color: Colors.white10),
                              FractionallySizedBox(
                                widthFactor: underline,
                                child: Container(height: 2, decoration: BoxDecoration(gradient: const LinearGradient(colors: [Colors.white70, Colors.white30]))),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 10),
                        // sequential dot loader
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Opacity(opacity: _dot1Opacity.value, child: _dotWidget()),
                            const SizedBox(width: 8),
                            Opacity(opacity: _dot2Opacity.value, child: _dotWidget()),
                            const SizedBox(width: 8),
                            Opacity(opacity: _dot3Opacity.value, child: _dotWidget()),
                          ],
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),

          // bottom caption (no blur, match app black so it blends)
          Positioned(
            left: 0,
            right: 0,
            bottom: 30,
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.black, // match background so it doesn't form a visible box
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'Designed · Minimal · Monochrome',
                  style: TextStyle(color: Colors.white.withOpacity(0.65), fontSize: 12, fontWeight: FontWeight.w500),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
