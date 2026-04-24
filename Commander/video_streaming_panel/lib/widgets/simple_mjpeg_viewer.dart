import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class SimpleMjpegViewer extends StatefulWidget {
  final String streamUrl;
  const SimpleMjpegViewer({Key? key, required this.streamUrl}) : super(key: key);
  
  @override
  State<SimpleMjpegViewer> createState() => _SimpleMjpegViewerState();
}

class _SimpleMjpegViewerState extends State<SimpleMjpegViewer> {
  Uint8List? _currentFrame;
  StreamSubscription? _subscription;
  Timer? _reconnectTimer;
  bool _isConnecting = false;
  
  @override
  void initState() {
    super.initState();
    _startStream();
  }
  
  void _startStream() async {
    if (_isConnecting) return;
    _isConnecting = true;
    
    try {
      final client = http.Client();
      final request = http.Request('GET', Uri.parse(widget.streamUrl));
      final response = await client.send(request);
      
      List<int> buffer = [];
      int jpegStart = -1;
      
      _subscription = response.stream.listen(
        (chunk) {
          buffer.addAll(chunk);
          
          for (int i = 0; i < buffer.length - 1; i++) {
            if (buffer[i] == 0xFF && buffer[i + 1] == 0xD8) {
              jpegStart = i;
            } else if (buffer[i] == 0xFF && buffer[i + 1] == 0xD9 && jpegStart >= 0) {
              final frame = Uint8List.fromList(buffer.sublist(jpegStart, i + 2));
              if (mounted) {
                setState(() => _currentFrame = frame);
              }
              buffer = buffer.sublist(i + 2);
              jpegStart = -1;
              break;
            }
          }
          
          if (buffer.length > 1000000) {
            buffer = buffer.sublist(buffer.length - 100000);
          }
        },
        onError: (e) {
          print('Stream error: $e - Reconnecting...');
          _scheduleReconnect();
        },
        onDone: () {
          print('Stream ended - Reconnecting...');
          _scheduleReconnect();
        },
      );
      
      _isConnecting = false;
    } catch (e) {
      print('Connection error: $e - Reconnecting...');
      _isConnecting = false;
      _scheduleReconnect();
    }
  }
  
  void _scheduleReconnect() {
    _subscription?.cancel();
    _reconnectTimer?.cancel();
    
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (mounted) {
        print('Attempting reconnect...');
        _startStream();
      }
    });
  }
  
  @override
  void dispose() {
    _subscription?.cancel();
    _reconnectTimer?.cancel();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (_currentFrame == null) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Connecting to camera...'),
          ],
        ),
      );
    }
    
    return Image.memory(
      _currentFrame!,
      fit: BoxFit.cover,
      gaplessPlayback: true,
      errorBuilder: (context, error, stackTrace) {
        return Center(
          child: Text('Error: $error'),
        );
      },
    );
  }
}
