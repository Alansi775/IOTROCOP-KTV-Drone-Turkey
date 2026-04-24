import 'package:flutter/material.dart';
import 'dart:ui';

class Joystick extends StatelessWidget {
  final String label;
  final double inputX;
  final double inputY;
  
  const Joystick({
    Key? key,
    this.label = '', // Varsayılan boş
    this.inputX = 0.0,
    this.inputY = 0.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    const double baseSize = 140.0;
    const double knobRange = 44.0;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: baseSize,
          height: baseSize,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // outer ring background
              Container(
                width: baseSize,
                height: baseSize,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.black.withOpacity(0.5),
                  boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 18, offset: Offset(0, 8))],
                ),
              ),
              // concentric rings + ticks
              Positioned.fill(
                child: CustomPaint(
                  painter: _CrosshairPainter(Colors.black.withOpacity(0.06)),
                ),
              ),
              // central guide dot
              Positioned(
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 6, offset: Offset(0, 3))],
                  ),
                ),
              ),
              // moving indicator
              Transform.translate(
                offset: Offset(inputX * knobRange, inputY * knobRange),
                child: Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    border: Border.all(color: Colors.black26, width: 0.8),
                    boxShadow: [
                      BoxShadow(color: Colors.black38, blurRadius: 8, offset: Offset(0, 6)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        // Label (sadece boş değilse göster)
        if (label.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            label,
            style: TextStyle(
              color: Colors.white70,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ],
    );
  }
}

class _CrosshairPainter extends CustomPainter {
  final Color color;
  _CrosshairPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color..strokeWidth = 1.0;
    final cx = size.width / 2;
    final cy = size.height / 2;
    canvas.drawLine(Offset(cx - 10, cy), Offset(cx + 10, cy), paint);
    canvas.drawLine(Offset(cx, cy - 10), Offset(cx, cy + 10), paint);
    paint.style = PaintingStyle.stroke;
    paint.strokeWidth = 0.8;
    canvas.drawCircle(Offset(cx, cy), size.width * 0.28, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
