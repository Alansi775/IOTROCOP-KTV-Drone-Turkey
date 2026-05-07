import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'dart:math' as math;
import '../services/gps_service.dart';

class GpsWidget extends StatelessWidget {
  final GpsData gpsData;
  final VoidCallback onTap;

  const GpsWidget({
    Key? key,
    required this.gpsData,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color statusColor = gpsData.hasFix ? Colors.greenAccent : Colors.redAccent;
    String statusText = gpsData.hasFix
        ? 'GPS KİLİTLİ'
        : (gpsData.satellites > 0 ? 'ARAMA...' : 'GPS YOK');

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.black.withOpacity(0.7),
          border: Border.all(color: statusColor, width: 2),
          boxShadow: [
            BoxShadow(
              color: statusColor.withOpacity(0.3),
              blurRadius: 12,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                FaIcon(
                  FontAwesomeIcons.satellite,
                  color: statusColor,
                  size: 18,
                ),
                const SizedBox(width: 8),
                Text(
                  '${gpsData.satellites}',
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  'SATS',
                  style: TextStyle(
                    color: statusColor.withOpacity(0.8),
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              statusText,
              style: TextStyle(
                color: statusColor,
                fontSize: 10,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Haritaya dokunun',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 8,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class GpsMapDialog extends StatefulWidget {
  final Stream<GpsData> gpsStream;
  final GpsData initialGpsData;

  const GpsMapDialog({
    Key? key,
    required this.gpsStream,
    required this.initialGpsData,
  }) : super(key: key);

  @override
  State<GpsMapDialog> createState() => _GpsMapDialogState();
}

class _GpsMapDialogState extends State<GpsMapDialog> {
  final MapController _mapController = MapController();
  late GpsData _currentGpsData;

  @override
  void initState() {
    super.initState();
    _currentGpsData = widget.initialGpsData;
    
    // استمع للتحديثات
    widget.gpsStream.listen((gpsData) {
      if (mounted) {
        setState(() {
          _currentGpsData = gpsData;
        });
      }
    });
    
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final targetZoom = _hasPosition ? 19.0 : 5.0;
      _mapController.move(LatLng(_displayLat, _displayLon), targetZoom);
    });
  }

  bool get _hasPosition {
    final lat = _currentGpsData.latitude;
    final lon = _currentGpsData.longitude;
    return (lat.abs() > 0.000001 || lon.abs() > 0.000001);
  }

  double get _displayLat => _hasPosition ? _currentGpsData.latitude : 41.0082;
  double get _displayLon => _hasPosition ? _currentGpsData.longitude : 28.9784;

  void _zoomToPosition() {
    final bool hasPos = _hasPosition;
    final double targetLat = hasPos ? _currentGpsData.latitude : 41.0082;
    final double targetLon = hasPos ? _currentGpsData.longitude : 28.9784;
    final double targetZoom = hasPos ? 19.0 : 14.0;
    _mapController.move(LatLng(targetLat, targetLon), targetZoom);
  }

  @override
  Widget build(BuildContext context) {
    // تصحيح الاتجاه: نطرح 90 درجة عشان يكون الشمال فوق
    final correctedHeading = (_currentGpsData.heading) * (math.pi / 180.0);

    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.8,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.95),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: _currentGpsData.hasFix ? Colors.greenAccent : Colors.redAccent,
            width: 2,
          ),
        ),
        child: Stack(
          children: [
            Positioned.fill(
              child: ClipRRect(
                borderRadius: const BorderRadius.all(Radius.circular(18)),
                child: FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: LatLng(_displayLat, _displayLon),
                    initialZoom: _hasPosition ? 19.0 : 5.0,
                    maxZoom: 19.0,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                      userAgentPackageName: 'com.example.drone_app',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: LatLng(_displayLat, _displayLon),
                          width: 80,
                          height: 80,
                          alignment: Alignment.center,
                          child: Transform.rotate(
                            angle: correctedHeading,
                            alignment: Alignment.center,
                            child: Icon(
                              Icons.navigation,
                              color: _currentGpsData.hasFix ? Colors.red : Colors.grey,
                              size: 40,
                              shadows: [
                                Shadow(
                                  color: Colors.black.withOpacity(0.5),
                                  blurRadius: 4,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: SafeArea(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.35),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(18),
                      topRight: Radius.circular(18),
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _currentGpsData.hasFix ? 'Drone GPS Konumu' : 'GPS Sinyali Yok',
                              style: TextStyle(
                                color: _currentGpsData.hasFix ? Colors.greenAccent : Colors.redAccent,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 6),
                            if (_currentGpsData.hasFix) ...[
                              Text(
                                'Enlem: ${_currentGpsData.latitude.toStringAsFixed(6)}°',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                              Text(
                                'Boylam: ${_currentGpsData.longitude.toStringAsFixed(6)}°',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                              Text(
                                'Yükseklik: ${_currentGpsData.altitude.toStringAsFixed(1)}m',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                              Text(
                                'Yön: ${_currentGpsData.heading.toStringAsFixed(1)}°',
                                style: const TextStyle(color: Colors.greenAccent, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ] else ...[
                              Text(
                                'Uydu sayısı: ${_currentGpsData.satellites}',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                            ],
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const FaIcon(FontAwesomeIcons.locationCrosshairs, color: Colors.white70, size: 18),
                        tooltip: 'Konuma Git',
                        onPressed: _zoomToPosition,
                      ),
                      IconButton(
                        icon: const FaIcon(FontAwesomeIcons.xmark, color: Colors.white70, size: 20),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
