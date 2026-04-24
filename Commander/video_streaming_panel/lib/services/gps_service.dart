import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

class GpsService {
  RawDatagramSocket? _gpsSocket;
  final StreamController<GpsData> _gpsController = StreamController<GpsData>.broadcast();
  
  Stream<GpsData> get gpsStream => _gpsController.stream;
  
  Future<void> start() async {
    try {
      _gpsSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 5658);
      print("🛰️ GPS Service Started: Port 5658");

      _gpsSocket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          Datagram? dg = _gpsSocket!.receive();
          if (dg != null) {
            _processGpsPacket(dg.data);
          }
        }
      });
    } catch (e) {
      print("❌ GPS Service Error: $e");
    }
  }

  void _processGpsPacket(Uint8List data) {
    try {
      String jsonString = utf8.decode(data);
      Map<String, dynamic> packet = jsonDecode(jsonString);

      // Support both formats
      Map<String, dynamic> gpsData;
      
      if (packet.containsKey('type') && packet['type'] == 'gps_update') {
        // Old format
        gpsData = packet['data'];
      } else {
        // New format (direct from Nvidia)
        gpsData = packet;
      }
      
      _gpsController.add(GpsData(
        latitude: (gpsData['latitude'] as num).toDouble(),
        longitude: (gpsData['longitude'] as num).toDouble(),
        altitude: (gpsData['altitude'] as num).toDouble(),
        satellites: gpsData['satellites'] as int,
        hasFix: gpsData['has_fix'] as bool,
      ));
      
      print("📍 GPS: ${gpsData['latitude']}, ${gpsData['longitude']} | Sats: ${gpsData['satellites']}");
    } catch (e) {
      print("⚠️ GPS packet parse error: $e");
    }
  }

  void dispose() {
    _gpsSocket?.close();
    _gpsController.close();
  }
}

class GpsData {
  final double latitude;
  final double longitude;
  final double altitude;
  final int satellites;
  final bool hasFix;

  GpsData({
    required this.latitude,
    required this.longitude,
    required this.altitude,
    required this.satellites,
    required this.hasFix,
  });
}
