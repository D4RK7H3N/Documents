import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class UploadService {
  static const _storage = FlutterSecureStorage();
  static const _baseUrl = 'http://10.0.2.2:8000/api';

  static Future<String?> _getToken() async {
    return await _storage.read(key: 'access_token');
  }

  static Future<Map<String, String>> _authHeaders() async {
    final token = await _getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<Map<String, dynamic>> getUploadUrl({
    required String filename,
  }) async {
    final uri = Uri.parse('$_baseUrl/upload-url/')
        .replace(queryParameters: {'filename': filename});
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(body['error'] ?? 'Failed to get upload URL');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  static Future<String> uploadImage({
    required File imageFile,
    void Function(double percent)? onProgress,
  }) async {
    final filename = imageFile.path.split('/').last.isNotEmpty
        ? imageFile.path.split('/').last
        : imageFile.path.split('\\').last;

    final uploadData = await getUploadUrl(filename: filename);
    final presignedUrl = uploadData['upload_url'] as String;
    final publicUrl = uploadData['public_url'] as String;

    final bytes = await imageFile.readAsBytes();

    final uploadResponse = await http
        .put(
          Uri.parse(presignedUrl),
          body: bytes,
          headers: {
            'Content-Type': _mimeType(filename),
          },
        )
        .timeout(const Duration(seconds: 30));

    if (![200, 201, 204].contains(uploadResponse.statusCode)) {
      throw Exception(
        'Upload failed with status ${uploadResponse.statusCode}',
      );
    }

    onProgress?.call(1.0);

    return publicUrl;
  }

  static String _mimeType(String filename) {
    final ext = filename.split('.').last.toLowerCase();
    switch (ext) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'webp':
        return 'image/webp';
      default:
        return 'application/octet-stream';
    }
  }
}
