import 'dart:io';
import 'dart:typed_data';
import 'dart:convert';

/// Simple UDP helper (not yet wired). Keep here if you later want to move
/// UDP logic out of UI. For now it's a light wrapper that can start/stop
/// listening and exposes a stream of received JSON maps.
class UdpService {
  RawDatagramSocket? _socket;
  StreamController<Map<String, dynamic>>? _controller;

  Future<void> start({int port = 5656}) async {
    _controller ??= StreamController.broadcast();
    _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, port);
    _socket!.listen((event) {
      if (event == RawSocketEvent.read) {
        final dg = _socket!.receive();
        if (dg != null) {
          try {
            final decoded = jsonDecode(utf8.decode(dg.data));
            if (decoded is Map<String, dynamic>) _controller?.add(decoded);
          } catch (_) {}
        }
      }
    });
  }

  Stream<Map<String, dynamic>> get stream => _controller?.stream ?? const Stream.empty();

  void stop() {
    _socket?.close();
    _socket = null;
    _controller?.close();
    _controller = null;
  }
}
