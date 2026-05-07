import 'dart:io';

void main() {
  final file = File('drone_control_page.dart');
  var content = file.readAsStringSync();
  
  // 1. نضيف متغير للـ Flight Mode بعد _isArmed
  if (!content.contains('String _flightMode')) {
    content = content.replaceFirst(
      'bool _isArmed = false;',
      '''bool _isArmed = false;
  
  // Flight Mode من SW6
  String _flightMode = 'manual';  // manual, takeoff, landing''',
    );
  }
  
  // 2. نضيف UDP listener لـ Port 5659
  if (!content.contains('_flightModeSocket')) {
    content = content.replaceFirst(
      'RawDatagramSocket? _joystickUdpSocket;',
      '''RawDatagramSocket? _joystickUdpSocket;
  RawDatagramSocket? _flightModeSocket;  // Port 5659''',
    );
    
    // نضيف start في initState
    content = content.replaceFirst(
      '_startGpsService();',
      '''_startGpsService();
    _startFlightModeListener();''',
    );
    
    // نضيف dispose
    content = content.replaceFirst(
      '_joystickUdpSocket?.close();',
      '''_joystickUdpSocket?.close();
    _flightModeSocket?.close();''',
    );
  }
  
  // 3. نضيف الـ listener function بعد _startJoystickListener
  if (!content.contains('_startFlightModeListener')) {
    final insertAfter = '''  }

  void _processJoystickPacket''';
    
    final newCode = '''  }

  Future<void> _startFlightModeListener() async {
    try {
      _flightModeSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 5659);
      print("🎮 Flight Mode Listener Started: Port 5659");

      _flightModeSocket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          Datagram? dg = _flightModeSocket!.receive();
          if (dg != null) {
            _processFlightModePacket(dg.data);
          }
        }
      });
    } catch (e) {
      print("❌ Flight Mode UDP Error: \$e");
    }
  }

  void _processFlightModePacket(Uint8List data) {
    try {
      String jsonString = utf8.decode(data);
      Map<String, dynamic> packet = jsonDecode(jsonString);
      
      String mode = packet['mode'] ?? 'manual';
      
      setState(() {
        _flightMode = mode;
      });
      
      print("🎮 Flight Mode: \$_flightMode");
    } catch (e) {
      print("⚠️ Flight mode packet parse error: \$e");
    }
  }

  void _processJoystickPacket''';
    
    content = content.replaceFirst(insertAfter, newCode);
  }
  
  // 4. نعدل _switchStateForIndex لعرض SW6 في صندوق 3
  content = content.replaceFirst(
    '''String _switchStateForIndex(int index) {
    // ARM/DISARM kutusu aktif switch ID'sine göre sağdaki kutuya yerleşsin
    if (index == 0) {
      return _isArmed ? 'ARM' : 'DISARM';
    }
    // Diğer kutular için aktif switch ID'sini gösterebilirsin
    return 'UNKNOWN';
  }''',
    '''String _switchStateForIndex(int index) {
    if (index == 0) {
      return _isArmed ? 'ARM' : 'DISARM';
    }
    if (index == 3) {
      // SW6 - Flight Mode
      if (_flightMode == 'manual') return 'MANUAL';
      if (_flightMode == 'takeoff' || _flightMode == 'takeoff_ready') return 'TAKEOFF';
      if (_flightMode == 'landing' || _flightMode == 'landing_ready') return 'LANDING';
      if (_flightMode == 'hover') return 'HOVER';
      if (_flightMode == 'armed') return 'ARMED';
      if (_flightMode == 'disarmed') return 'DISARMED';
      return _flightMode.toUpperCase();
    }
    return 'UNKNOWN';
  }''',
  );
  
  // 5. نعدل _switchColorForIndex لتلوين SW6
  content = content.replaceFirst(
    '''Color _switchColorForIndex(int index) {
    if (index == 0) return _isArmed ? Colors.green : Colors.grey;  // Sağdaki ilk kutu
    return Colors.grey.shade700;
  }''',
    '''Color _switchColorForIndex(int index) {
    if (index == 0) return _isArmed ? Colors.green : Colors.grey;
    if (index == 3) {
      // SW6 colors
      if (_flightMode == 'takeoff' || _flightMode == 'takeoff_ready') return Colors.green;
      if (_flightMode == 'landing' || _flightMode == 'landing_ready') return Colors.orange;
      if (_flightMode == 'hover') return Colors.blue;
      return Colors.grey;
    }
    return Colors.grey.shade700;
  }''',
  );
  
  file.writeAsStringSync(content);
  print('✅ Patched!');
}
