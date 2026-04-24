import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class MjpegStream extends StatefulWidget {
  final String streamUrl;
  const MjpegStream({Key? key, required this.streamUrl}) : super(key: key);

  @override
  State<MjpegStream> createState() => _MjpegStreamState();
}

class _MjpegStreamState extends State<MjpegStream> {
  Uint8List? _currentFrame;
  bool _isLoading = true;
  String? _errorMessage;
  StreamSubscription? _streamSubscription;
  final http.Client _client = http.Client();

  @override
  void initState() {
    super.initState();
    _startStream();
  }

  Future<void> _startStream() async {
    if (!mounted) return;
    setState(() { _isLoading = true; _errorMessage = null; });

    try {
      final request = http.Request('GET', Uri.parse(widget.streamUrl));
      final response = await _client.send(request);

      if (response.statusCode != 200) {
        if (mounted) setState(() { _errorMessage = 'Hata: ${response.statusCode}'; _isLoading = false; });
        return;
      }

      List<int> buffer = [];
      _streamSubscription = response.stream.listen(
        (chunk) {
          buffer.addAll(chunk);
          while (buffer.length > 2) {
            final startIdx = _findMarker(buffer, [0xFF, 0xD8]);
            if (startIdx == -1) { buffer.clear(); break; }
            final endIdx = _findMarker(buffer, [0xFF, 0xD9], startIdx + 2);
            if (endIdx == -1) break;
            final frameBytes = buffer.sublist(startIdx, endIdx + 2);
            if (mounted) setState(() { _currentFrame = Uint8List.fromList(frameBytes); _isLoading = false; });
            buffer = buffer.sublist(endIdx + 2);
          }
        },
        onError: (e) { if (mounted) Future.delayed(const Duration(seconds: 2), _startStream); },
        onDone: () { if (mounted) _startStream(); },
      );
    } catch (e) {
      if (mounted) setState(() { _errorMessage = 'Bağlantı Yok'; _isLoading = false; });
    }
  }

  int _findMarker(List<int> data, List<int> marker, [int startFrom = 0]) {
    for (int i = startFrom; i <= data.length - marker.length; i++) {
      bool found = true;
      for (int j = 0; j < marker.length; j++) {
        if (data[i + j] != marker[j]) { found = false; break; }
      }
      if (found) return i;
    }
    return -1;
  }

  @override
  void dispose() {
    _streamSubscription?.cancel();
    _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Container(
        color: Colors.black,
        child: const Center(
          child: CircularProgressIndicator(color: Color(0xFF00D9FF)),
        ),
      );
    }
    
    if (_errorMessage != null) {
      return Container(
        color: Colors.black,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.videocam_off, color: Colors.red, size: 50),
              const SizedBox(height: 10),
              Text(_errorMessage!, style: const TextStyle(color: Colors.white)),
              TextButton(
                onPressed: _startStream,
                child: const Text('Yenile', style: TextStyle(color: Color(0xFF00D9FF))),
              ),
            ],
          ),
        ),
      );
    }
    
    return _currentFrame == null
        ? Container(color: Colors.black)
        : Image.memory(
            _currentFrame!,
            fit: BoxFit.cover,
            gaplessPlayback: true,
          );
  }
}