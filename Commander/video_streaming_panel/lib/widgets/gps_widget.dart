import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
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
  final GpsData gpsData;

  const GpsMapDialog({Key? key, required this.gpsData}) : super(key: key);

  @override
  State<GpsMapDialog> createState() => _GpsMapDialogState();
}

class _GpsMapDialogState extends State<GpsMapDialog> {
  final MapController _mapController = MapController();

  bool get _hasPosition {
    final lat = widget.gpsData.latitude;
    final lon = widget.gpsData.longitude;
    return (lat.abs() > 0.000001 || lon.abs() > 0.000001);
  }

  double get _displayLat => _hasPosition ? widget.gpsData.latitude : 41.0082;
  double get _displayLon => _hasPosition ? widget.gpsData.longitude : 28.9784;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final targetZoom = _hasPosition ? 19.0 : 5.0;
      _mapController.move(LatLng(_displayLat, _displayLon), targetZoom);
    });
  }

  void _zoomToPosition() {
    final bool hasPos = _hasPosition;
    final double targetLat = hasPos ? widget.gpsData.latitude : 41.0082;
    final double targetLon = hasPos ? widget.gpsData.longitude : 28.9784;
    final double targetZoom = hasPos ? 19.0 : 14.0;
    _mapController.move(LatLng(targetLat, targetLon), targetZoom);
  }

  @override
  Widget build(BuildContext context) {
    final gpsData = widget.gpsData;

    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.8,
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.95),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: gpsData.hasFix ? Colors.greenAccent : Colors.redAccent,
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
                          width: 50,
                          height: 50,
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              FaIcon(
                                (gpsData.hasFix
                                    ? FontAwesomeIcons.plane
                                    : (_hasPosition ? FontAwesomeIcons.plane : FontAwesomeIcons.questionCircle)),
                                color: gpsData.hasFix
                                    ? Colors.red
                                    : (_hasPosition ? Colors.orange : Colors.grey),
                                size: 30,
                              ),
                              if (gpsData.hasFix)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.red,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text(
                                    'İHA',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 8,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                            ],
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
                              gpsData.hasFix ? 'Drone GPS Konumu' : 'GPS Sinyali Yok',
                              style: TextStyle(
                                color: gpsData.hasFix ? Colors.greenAccent : Colors.redAccent,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 6),
                            if (gpsData.hasFix) ...[
                              Text(
                                'Enlem: ${gpsData.latitude.toStringAsFixed(6)}°',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                              Text(
                                'Boylam: ${gpsData.longitude.toStringAsFixed(6)}°',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                              Text(
                                'Yükseklik: ${gpsData.altitude.toStringAsFixed(1)}m',
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                              ),
                            ] else ...[
                              Text(
                                'Uydu sayısı: ${gpsData.satellites}',
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
