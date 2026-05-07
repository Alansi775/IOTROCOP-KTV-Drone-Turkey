import 'package:video_streaming_panel/widgets/simple_mjpeg_viewer.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../widgets/joystick.dart';
import '../widgets/throttle_control.dart';
import '../widgets/gps_widget.dart';
import '../services/gps_service.dart';

class DroneControlPage extends StatefulWidget {
  const DroneControlPage({Key? key}) : super(key: key);

  @override
  State<DroneControlPage> createState() => _DroneControlPageState();
}

class _DroneControlPageState extends State<DroneControlPage> {
  static const String bridgeStreamUrl = 'http://192.168.100.1:8080/video_feed';

  // UDP Listener - Port 5657 (Python Flutter Bridge)
  RawDatagramSocket? _joystickUdpSocket;

  // Joystick data
  double _droneX = 0.0;
  double _droneY = 0.0;
  double _compX = 0.0;
  double _compY = 0.0;
  double _power = 0.0;

  // Extra sensor data
  int _pot1 = 0;
  int _pot2 = 0;
  int _switches = 0;

  // ARM/DISARM state (hangi switch'e bağlıysa onun ID'si)
  int _armSwitchId = 12; // SW12 aktif olduğunda ARM
  bool _isArmed = false;

  // Connection status
  bool _isConnected = false;
  DateTime? _lastPacketTime;
  Timer? _connectionWatchdog;

  // GPS Service
  final GpsService _gpsService = GpsService();
  GpsData _gpsData = GpsData(
    latitude: 0.0,
    longitude: 0.0,
    altitude: 0.0,
    satellites: 0,
    hasFix: false,
  );

  // Side-specific overlays - زرين منفصلين
  bool _showLeftOverlays = false;
  bool _showRightOverlays = false;

  // Draggable throttle position
  Offset? _throttlePos;
  static const double _throttleW = 90.0;
  static const double _throttleH = 220.0;

  @override
  void initState() {
    super.initState();
    _startJoystickListener();
    _startGpsService();
    _startConnectionWatchdog();
  }

  Future<void> _startGpsService() async {
    await _gpsService.start();
    _gpsService.gpsStream.listen((gpsData) {
      setState(() {
        _gpsData = gpsData;
      });
    });
  }

  Future<void> _startJoystickListener() async {
    try {
      _joystickUdpSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 5657);
      print("🎮 Flutter Bridge UDP Listener Started: Port 5657");

      _joystickUdpSocket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          Datagram? dg = _joystickUdpSocket!.receive();
          if (dg != null) {
            _processJoystickPacket(dg.data);
          }
        }
      });
    } catch (e) {
      print("❌ Flutter Bridge UDP Error: $e");
    }
  }

  void _processJoystickPacket(Uint8List data) {
    try {
      String jsonString = utf8.decode(data);
      Map<String, dynamic> packet = jsonDecode(jsonString);

      if (packet['type'] == 'joystick_update') {
        Map<String, dynamic> joystickData = packet['data'];

        setState(() {
          double rawLeftX = (joystickData['joystick_left']['x'] as num).toDouble();
          double rawLeftY = (joystickData['joystick_left']['y'] as num).toDouble();
          _droneX = -rawLeftX;
          _droneY = rawLeftY;

          double rawRightX = (joystickData['joystick_right']['x'] as num).toDouble();
          double rawRightY = (joystickData['joystick_right']['y'] as num).toDouble();
          _compX = -rawRightX;
          _compY = rawRightY;

          _power = (joystickData['power'] as num).toDouble();

          if (joystickData.containsKey('potentiometers')) {
            _pot1 = joystickData['potentiometers']['pot1'] as int;
            _pot2 = joystickData['potentiometers']['pot2'] as int;
          }
          if (joystickData.containsKey('switches')) {
            // Yeni Python format: switches artık Map<String, bool>
            if (joystickData['switches'] is Map) {
              Map<String, dynamic> switches = joystickData['switches'];
              // ARM/DISARM için _armSwitchId'yi kullan
              _isArmed = switches['switch_${_armSwitchId}'] ?? false;
              // Eski raw değeri de kaydet (backward compatibility)
              if (joystickData.containsKey('switches_raw')) {
                _switches = joystickData['switches_raw'] as int;
              }
            } else {
              // Eski format desteği (sadece int)
              _switches = joystickData['switches'] as int;
              _isArmed = ((_switches >> _armSwitchId) & 0x1) == 1;
            }
          }

          _isConnected = true;
          _lastPacketTime = DateTime.now();
        });
      }
    } catch (e) {
      print("⚠️ Joystick packet parse error: $e");
    }
  }

  void _startConnectionWatchdog() {
    _connectionWatchdog = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_lastPacketTime != null) {
        final age = DateTime.now().difference(_lastPacketTime!).inSeconds;
        if (age > 2) {
          setState(() {
            _isConnected = false;
          });
        }
      }
    });
  }

  void _showMapDialog() {
    showDialog(
      context: context,
      builder: (context) => GpsMapDialog(gpsData: _gpsData),
    );
  }

  @override
  void dispose() {
    _joystickUdpSocket?.close();
    _gpsService.dispose();
    _connectionWatchdog?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. Background - Video Stream
          Positioned.fill(
            child: SimpleMjpegViewer(streamUrl: bridgeStreamUrl),
          ),

          // 2. Top Bar - Buttons
          Positioned(
            top: 20,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildVisibleButton(FontAwesomeIcons.arrowUp, 'KALKIŞ', Colors.green),
                    const SizedBox(height: 10),
                    _buildVisibleButton(FontAwesomeIcons.arrowDown, 'İNİŞ', Colors.orange),
                    const SizedBox(height: 10),
                    _buildVisibleButton(FontAwesomeIcons.house, 'RETURN', Colors.blue),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _buildConnectionIndicator(),
                    const SizedBox(height: 10),
                    _buildVisibleButton(FontAwesomeIcons.gear, 'AYAR', Colors.grey),
                  ],
                ),
              ],
            ),
          ),

          // GPS Widget - Top Center
          Positioned(
            top: 20,
            left: 0,
            right: 0,
            child: Center(
              child: GpsWidget(
                gpsData: _gpsData,
                onTap: _showMapDialog,
              ),
            ),
          ),

          // 3. Bottom Controls - Joysticks (rearranged)
          // Left side: Throttle (horizontal, draggable) - placeholder space
          // Center: Right joystick (drone control)
          // Right side: Left joystick (camera/compass)
          Positioned(
            bottom: 25,
            left: 0,
            right: 0,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 35),
              child: Opacity(
                opacity: 0.9,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Left: Horizontal Throttle placeholder (actual is draggable below)
                    SizedBox(width: _throttleH, height: _throttleW), // swapped dimensions
                    // Center: Drone joystick (was right, now center)
                    IgnorePointer(
                      ignoring: true,
                      child: Joystick(
                        label: '',
                        inputX: _compX,
                        inputY: _compY,
                      ),
                    ),
                    // Right: Camera joystick (was left, now right)
                    IgnorePointer(
                      ignoring: true,
                      child: Joystick(
                        label: '',
                        inputX: _droneX,
                        inputY: _droneY,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Draggable Horizontal Throttle (on the left side, bottom)
          Builder(builder: (context) {
            final size = MediaQuery.of(context).size;
            // Throttle أفقي: عرض 200، ارتفاع 80
            final throttleWidth = 200.0;
            final throttleHeight = 80.0;
            
            if (_throttlePos == null) {
              final bottomPad = MediaQuery.of(context).padding.bottom;
              _throttlePos = Offset(
                35, // يسار - نفس padding الـ joysticks
                size.height - throttleHeight - 25 - bottomPad, // تحت - محاذي مع الـ joysticks
              );
            }

            return Positioned(
              left: _throttlePos!.dx,
              top: _throttlePos!.dy,
              child: GestureDetector(
                onPanUpdate: (details) {
                  setState(() {
                    final bottomPad = MediaQuery.of(context).padding.bottom;
                    final maxTop = size.height - throttleHeight - 16.0 - bottomPad;
                    _throttlePos = Offset(
                      (_throttlePos!.dx + details.delta.dx).clamp(8.0, size.width - throttleWidth - 8.0),
                      (_throttlePos!.dy + details.delta.dy).clamp(8.0, maxTop),
                    );
                  });
                },
                child: SizedBox(
                  width: throttleWidth,
                  height: throttleHeight,
                  child: ThrottleControl(
                    inputValue: _power,
                    showLabel: false,
                    horizontal: true, // الوضع الأفقي الجديد
                  ),
                ),
              ),
            );
          }),

          // ============ RIGHT SIDE OVERLAY ============
          // Right side lines (always rendered, opacity controlled)
          Positioned.fill(
            child: IgnorePointer(
              child: AnimatedOpacity(
                opacity: _showRightOverlays ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 800),
                child: CustomPaint(
                  painter: _SwitchLinesPainter(
                    _computeRightPoints(context),
                    isRightSide: true,
                  ),
                ),
              ),
            ),
          ),

          // Right side boxes - ALWAYS in tree for animation to work
          ..._buildRightBoxesAnimated(context),

          // ============ LEFT SIDE OVERLAY ============
          // Left side lines (always rendered, opacity controlled)
          Positioned.fill(
            child: IgnorePointer(
              child: AnimatedOpacity(
                opacity: _showLeftOverlays ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 800),
                child: CustomPaint(
                  painter: _SwitchLinesPainter(
                    _computeLeftPoints(context),
                    isRightSide: false,
                  ),
                ),
              ),
            ),
          ),

          // Left side boxes - ALWAYS in tree for animation to work
          ..._buildLeftBoxesAnimated(context),

          // Background tap to hide overlays
          if (_showLeftOverlays || _showRightOverlays)
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => setState(() {
                  _showLeftOverlays = false;
                  _showRightOverlays = false;
                }),
                child: const SizedBox.expand(),
              ),
            ),

          // ============ TOGGLE BUTTONS ============
          // Left toggle button - ينسحب مع الصناديق
          AnimatedPositioned(
            duration: const Duration(milliseconds: 1000),
            curve: Curves.easeOutExpo,
            left: _showLeftOverlays ? 150 : 8, // ينسحب للداخل لما يفتح
            top: size.height / 2 - 28,
            child: GestureDetector(
              onTap: () => setState(() {
                _showLeftOverlays = !_showLeftOverlays;
                if (_showLeftOverlays) _showRightOverlays = false;
              }),
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: _showLeftOverlays ? Colors.white30 : Colors.white10,
                    width: 1.5,
                  ),
                ),
                child: Icon(
                  _showLeftOverlays ? Icons.chevron_left : Icons.chevron_right,
                  color: Colors.white70,
                  size: 32,
                ),
              ),
            ),
          ),

          // Right toggle button - ينسحب مع الصناديق
          AnimatedPositioned(
            duration: const Duration(milliseconds: 1000),
            curve: Curves.easeOutExpo,
            right: _showRightOverlays ? 150 : 8, // ينسحب للداخل لما يفتح
            top: size.height / 2 - 28,
            child: GestureDetector(
              onTap: () => setState(() {
                _showRightOverlays = !_showRightOverlays;
                if (_showRightOverlays) _showLeftOverlays = false;
              }),
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: _showRightOverlays ? Colors.white30 : Colors.white10,
                    width: 1.5,
                  ),
                ),
                child: Icon(
                  _showRightOverlays ? Icons.chevron_right : Icons.chevron_left,
                  color: Colors.white70,
                  size: 32,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ============ COMPUTE POINTS ============
  
  List<Offset> _computeRightPoints(BuildContext context) {
    final size = MediaQuery.of(context).size;
    const boxW = 124.0;
    const boxH = 48.0;
    const spacing = 60.0;
    final totalHeight = 4 * boxH + 3 * spacing;
    final topPad = MediaQuery.of(context).padding.top + 20.0;
    final reservedBottom = 60.0 + _throttleH;
    double startY = size.height - reservedBottom - totalHeight;
    final minTop = topPad + 48.0;
    if (startY < minTop + 40.0) startY = minTop + 40.0;
    startY = startY + 60.0;
    startY = startY.clamp(minTop + 40.0, size.height - totalHeight - 8.0);

    List<Offset> points = [];
    for (int i = 0; i < 4; i++) {
      final x = size.width - 16 - boxW / 2;
      final y = startY + i * (boxH + spacing) + boxH / 2;
      points.add(Offset(x, y));
    }
    return points;
  }

  List<Offset> _computeLeftPoints(BuildContext context) {
    final size = MediaQuery.of(context).size;
    const boxW = 124.0;
    const boxH = 48.0;
    const spacing = 60.0;
    final totalHeight = 4 * boxH + 3 * spacing;
    final topPad = MediaQuery.of(context).padding.top + 20.0;
    final reservedBottom = 60.0 + _throttleH;
    double startY = size.height - reservedBottom - totalHeight;
    final minTop = topPad + 48.0;
    if (startY < minTop + 40.0) startY = minTop + 40.0;
    startY = startY + 60.0;
    startY = startY.clamp(minTop + 40.0, size.height - totalHeight - 8.0);

    List<Offset> points = [];
    for (int i = 0; i < 4; i++) {
      final x = 16 + boxW / 2;
      final y = startY + i * (boxH + spacing) + boxH / 2;
      points.add(Offset(x, y));
    }
    return points;
  }

  // ============ BUILD ANIMATED BOXES ============

  List<Widget> _buildRightBoxesAnimated(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final points = _computeRightPoints(context);
    const boxW = 124.0;
    const boxH = 48.0;

    List<Widget> boxes = [];
    for (int i = 0; i < points.length; i++) {
      final center = points[i];
      final targetLeft = size.width - 16 - boxW;
      final targetTop = center.dy - boxH / 2;
      final hiddenLeft = size.width + 50; // خارج الشاشة من اليمين

      boxes.add(
        AnimatedPositioned(
          duration: Duration(milliseconds: 1200 + i * 150), // بطيء جداً
          curve: Curves.easeOutExpo, // منحنى بطيء وناعم
          left: _showRightOverlays ? targetLeft : hiddenLeft,
          top: targetTop,
          child: IgnorePointer(
            ignoring: !_showRightOverlays, // يتجاهل اللمس لما يكون مخفي
            child: AnimatedOpacity(
              duration: Duration(milliseconds: 800 + i * 100),
              curve: Curves.easeOut,
              opacity: _showRightOverlays ? 1.0 : 0.0,
              child: _buildSingleSwitchBox(i, boxW, boxH),
            ),
          ),
        ),
      );
    }
    return boxes;
  }

  List<Widget> _buildLeftBoxesAnimated(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final points = _computeLeftPoints(context);
    const boxW = 124.0;
    const boxH = 48.0;

    List<Widget> boxes = [];
    for (int i = 0; i < points.length; i++) {
      final center = points[i];
      final targetLeft = 16.0;
      final targetTop = center.dy - boxH / 2;
      final hiddenLeft = -boxW - 50; // خارج الشاشة من اليسار

      boxes.add(
        AnimatedPositioned(
          duration: Duration(milliseconds: 1200 + i * 150), // بطيء جداً
          curve: Curves.easeOutExpo, // منحنى بطيء وناعم
          left: _showLeftOverlays ? targetLeft : hiddenLeft,
          top: targetTop,
          child: IgnorePointer(
            ignoring: !_showLeftOverlays, // يتجاهل اللمس لما يكون مخفي
            child: AnimatedOpacity(
              duration: Duration(milliseconds: 800 + i * 100),
              curve: Curves.easeOut,
              opacity: _showLeftOverlays ? 1.0 : 0.0,
              child: _buildSingleSwitchBox(4 + i, boxW, boxH), // indices 4-7 for left
            ),
          ),
        ),
      );
    }
    return boxes;
  }

  Widget _buildSingleSwitchBox(int index, double w, double h) {
    final state = _switchStateForIndex(index);
    final color = _switchColorForIndex(index);
    return GestureDetector(
      onTap: () {
        setState(() {
          _showLeftOverlays = false;
          _showRightOverlays = false;
        });
      },
      child: Container(
        width: w,
        height: h,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.5),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.8), width: 1.5),
        ),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            state,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }

  String _switchStateForIndex(int index) {
    // ARM/DISARM kutusu aktif switch ID'sine göre sağdaki kutuya yerleşsin
    if (index == 0) {
      return _isArmed ? 'ARM' : 'DISARM';
    }
    // Diğer kutular için aktif switch ID'sini gösterebilirsin
    return 'UNKNOWN';
  }

  Color _switchColorForIndex(int index) {
    if (index == 0) return _isArmed ? Colors.green : Colors.grey;  // Sağdaki ilk kutu
    return Colors.grey.shade700;
  }

  Widget _buildConnectionIndicator() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.black.withOpacity(0.6),
        border: Border.all(
          color: _isConnected ? Colors.greenAccent : Colors.redAccent,
          width: 2,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: _isConnected ? Colors.greenAccent : Colors.redAccent,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: _isConnected
                      ? Colors.greenAccent.withOpacity(0.5)
                      : Colors.redAccent.withOpacity(0.5),
                  blurRadius: 8,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            _isConnected ? 'LIVE' : 'NO DATA',
            style: TextStyle(
              color: _isConnected ? Colors.greenAccent : Colors.redAccent,
              fontSize: 10,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVisibleButton(IconData icon, String label, Color accentColor) {
    return GestureDetector(
      onTap: () {
        print('$label butonuna basıldı');
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.black.withOpacity(0.55),
          border: Border.all(color: Colors.white10, width: 1),
          boxShadow: const [
            BoxShadow(color: Colors.black54, blurRadius: 20, offset: Offset(0, 6)),
            BoxShadow(color: Colors.white10, blurRadius: 8, spreadRadius: 0),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (label == 'RETURN')
              SizedBox(
                width: 36,
                height: 36,
                child: Image.asset(
                  'assets/icons/returntohome.png',
                  fit: BoxFit.contain,
                  color: Colors.white70,
                  colorBlendMode: BlendMode.srcIn,
                  errorBuilder: (ctx, err, stack) =>
                      const FaIcon(FontAwesomeIcons.house, color: Colors.white70, size: 22),
                ),
              )
            else
              FaIcon(icon, color: Colors.white70, size: 18),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.6,
              ),
            ),
            const SizedBox(width: 6),
          ],
        ),
      ),
    );
  }
}

// ============ PAINTER - Same logic as old working code ============
class _SwitchLinesPainter extends CustomPainter {
  final List<Offset> boxCenters;
  final bool isRightSide;

  _SwitchLinesPainter(this.boxCenters, {required this.isRightSide});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..strokeCap = StrokeCap.round
      ..color = Colors.grey.withOpacity(0.7);

    for (int i = 0; i < boxCenters.length; i++) {
      final p = boxCenters[i];
      
      // نفس منطق الكود القديم:
      // صناديق اليمين -> خط يذهب لحافة اليمين
      // صناديق اليسار -> خط يذهب لحافة اليسار
      final target = Offset(isRightSide ? size.width - 8 : 8, p.dy);
      
      // منحنى خفيف
      final mid = Offset((p.dx + target.dx) / 2, p.dy - 12);
      final path = Path()..moveTo(p.dx, p.dy);
      path.quadraticBezierTo(mid.dx, mid.dy, target.dx, target.dy);
      canvas.drawPath(path, paint);
      
      // دائرة صغيرة عند الحافة
      final fill = Paint()..color = Colors.grey.withOpacity(0.8);
      canvas.drawCircle(target, 3.0, fill);
    }
  }

  @override
  bool shouldRepaint(covariant _SwitchLinesPainter oldDelegate) =>
      oldDelegate.boxCenters != boxCenters || oldDelegate.isRightSide != isRightSide;
}