import 'package:flutter/material.dart';

class ThrottleControl extends StatelessWidget {
  final double inputValue;
  final bool showLabel;
  final bool horizontal; // جديد: وضع أفقي

  const ThrottleControl({
    Key? key, 
    this.inputValue = 0.0,
    this.showLabel = false,
    this.horizontal = false, // افتراضي عمودي
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final double value = inputValue.clamp(0.0, 1.0);

    // إذا كان أفقي، استخدم البناء الأفقي
    if (horizontal) {
      return _buildHorizontal(context, value);
    }

    // البناء العمودي الأصلي
    return _buildVertical(context, value);
  }

  // ============ الوضع الأفقي ============
  Widget _buildHorizontal(BuildContext context, double value) {
    return LayoutBuilder(builder: (context, constraints) {
      final double maxWidth = constraints.maxWidth.isFinite ? constraints.maxWidth : 220.0;
      final double height = constraints.maxHeight.isFinite ? constraints.maxHeight : 90.0;

      return SizedBox(
        width: maxWidth,
        height: height,
        child: Container(
          width: maxWidth,
          height: height,
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.55),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white10, width: 1),
            boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 16, offset: const Offset(0, 8))]
          ),
          child: Stack(
            children: [
              // Grid - خطوط أفقية
              Positioned.fill(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: List.generate(6, (index) => 
                      Container(
                        height: 1, 
                        color: Colors.white.withOpacity(0.1), 
                        margin: const EdgeInsets.symmetric(horizontal: 8),
                      )
                    ),
                  ),
                ),
              ),
              
              // Level markers - أفقية في اليسار
              Positioned(
                left: 8,
                top: height * 0.25 - 2,
                child: _HorizontalLevelMarker(value: value, markerPos: 0.66),
              ),
              Positioned(
                left: 8,
                top: height * 0.55 - 2,
                child: _HorizontalLevelMarker(value: value, markerPos: 0.33),
              ),
              
              // Fill - يتعبى من اليسار لليمين
              Positioned(
                left: 4,
                top: 4,
                bottom: 28, // مساحة للرقم تحت
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 100),
                  width: (maxWidth - 8) * value,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(6),
                    gradient: LinearGradient(
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                      colors: [Colors.white24, Colors.white10],
                    ),
                    boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 12, spreadRadius: 1)]
                  ),
                ),
              ),
              
              // Percentage text - في النص تحت
              Positioned(
                left: 0,
                right: 0,
                bottom: 4,
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: _getThrottleColor(value), width: 1)
                    ),
                    child: Text(
                      '%${(value * 100).toInt()}',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  // ============ الوضع العمودي الأصلي ============
  Widget _buildVertical(BuildContext context, double value) {
    return LayoutBuilder(builder: (context, constraints) {
      final double width = constraints.maxWidth.isFinite ? constraints.maxWidth : 80.0;
      final double maxHeight = constraints.maxHeight.isFinite ? constraints.maxHeight : 220.0;
      final double labelArea = showLabel ? 40.0 : 0.0;
      final double containerHeight = (maxHeight - labelArea).clamp(60.0, maxHeight - 8.0);

      return SizedBox(
        width: width,
        height: maxHeight,
        child: Column(
          mainAxisSize: MainAxisSize.max,
          children: [
            Container(
              width: width,
              height: containerHeight,
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.55),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white10, width: 1),
                boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 16, offset: const Offset(0, 8))]
              ),
              child: Stack(
                alignment: Alignment.bottomCenter,
                children: [
                  // Grid
                  Positioned.fill(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: List.generate(10, (index) => 
                        Container(height: 1, color: Colors.white.withOpacity(0.1), margin: const EdgeInsets.symmetric(horizontal: 4))
                      ),
                    ),
                  ),
                  // level markers
                  Positioned(
                    left: 6,
                    bottom: (containerHeight - 8) * 0.33 - 6,
                    child: _LevelMarker(value: value, markerPos: 0.33),
                  ),
                  Positioned(
                    left: 6,
                    bottom: (containerHeight - 8) * 0.66 - 6,
                    child: _LevelMarker(value: value, markerPos: 0.66),
                  ),
                  // Fill
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 100),
                    width: width - 8,
                    height: (containerHeight - 8) * value,
                    margin: const EdgeInsets.only(bottom: 4),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(6),
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [Colors.white24, Colors.white10],
                      ),
                      boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 12, spreadRadius: 1)]
                    ),
                  ),
                  // Percentage text
                  Positioned(
                    bottom: ((containerHeight - 30) * value).clamp(6, containerHeight - 30),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.8),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: _getThrottleColor(value), width: 1)
                      ),
                      child: Text(
                        '%${(value * 100).toInt()}',
                        style: const TextStyle(
                          color: Colors.white70,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Label
            if (showLabel) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white10, width: 1),
                ),
                child: const FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    'THRUST',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      );
    });
  }

  Color _getThrottleColor(double value) {
    if (value < 0.40) return const Color(0xFF00FF41);
    if (value < 0.75) return const Color(0xFFFFD700);
    return const Color(0xFFFF0033);
  }
}

// ============ Vertical Level Marker (Original) ============
class _LevelMarker extends StatelessWidget {
  final double value;
  final double markerPos;
  const _LevelMarker({Key? key, required this.value, required this.markerPos}) : super(key: key);

  Color _upColor() => const Color(0xFF6EE7B7);
  Color _downColor() => const Color(0xFFFAA2A2);
  Color _neutralFill() => Colors.white10;
  Color _neutralBorder() => Colors.white24;

  @override
  Widget build(BuildContext context) {
    const double h = 0.06;
    final double pos = markerPos.clamp(0.0, 1.0);
    final bool isAbove = value > (pos + h);
    final bool isBelow = value < (pos - h);

    final Color fill = isAbove ? _upColor() : (isBelow ? _downColor() : _neutralFill());
    final Color border = isAbove ? _upColor().withOpacity(0.95) : (isBelow ? _downColor().withOpacity(0.95) : _neutralBorder());

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      width: 18,
      height: 4,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(2.5),
        color: fill,
        border: Border.all(color: border, width: 1.0),
        boxShadow: [
          if (isAbove || isBelow) BoxShadow(color: border.withOpacity(0.14), blurRadius: 6, spreadRadius: 0.6),
        ],
      ),
    );
  }
}

// ============ Horizontal Level Marker (New) ============
class _HorizontalLevelMarker extends StatelessWidget {
  final double value;
  final double markerPos;
  const _HorizontalLevelMarker({Key? key, required this.value, required this.markerPos}) : super(key: key);

  Color _upColor() => const Color(0xFF6EE7B7);
  Color _downColor() => const Color(0xFFFAA2A2);
  Color _neutralFill() => Colors.white10;
  Color _neutralBorder() => Colors.white24;

  @override
  Widget build(BuildContext context) {
    const double h = 0.06;
    final double pos = markerPos.clamp(0.0, 1.0);
    final bool isAbove = value > (pos + h);
    final bool isBelow = value < (pos - h);

    final Color fill = isAbove ? _upColor() : (isBelow ? _downColor() : _neutralFill());
    final Color border = isAbove ? _upColor().withOpacity(0.95) : (isBelow ? _downColor().withOpacity(0.95) : _neutralBorder());

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      width: 18,  // عرض كبير - أفقي
      height: 4,  // ارتفاع صغير - أفقي
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(2.5),
        color: fill,
        border: Border.all(color: border, width: 1.0),
        boxShadow: [
          if (isAbove || isBelow) BoxShadow(color: border.withOpacity(0.14), blurRadius: 6, spreadRadius: 0.6),
        ],
      ),
    );
  }
}