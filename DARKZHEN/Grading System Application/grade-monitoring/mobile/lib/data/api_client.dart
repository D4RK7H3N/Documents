import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../domain/models.dart';
import 'token_storage.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class LoginResult {
  final String access;
  final String refresh;
  final AppUser user;
  final bool mustChangePassword;

  LoginResult({
    required this.access,
    required this.refresh,
    required this.user,
    required this.mustChangePassword,
  });
}

class ApiClient {
  final String baseUrl;
  final TokenStorage storage;

  ApiClient({required this.baseUrl, required this.storage});

  Future<HttpClientRequest> _open(String method, String path) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 15);
    return client.openUrl(method, Uri.parse('$baseUrl$path'));
  }

  Future<Map<String, dynamic>> _send(HttpClientRequest request,
      {String? access, Object? body}) async {
    if (access != null) request.headers.set('Authorization', 'Bearer $access');
    if (body != null) {
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode(body));
    }
    final response = await request.close();
    final text = await response.transform(utf8.decoder).join();
    Map<String, dynamic>? data;
    if (text.isNotEmpty) {
      try {
        data = jsonDecode(text) as Map<String, dynamic>;
      } catch (_) {}
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error = data?['error'];
      throw ApiException(
        response.statusCode,
        error is Map
            ? (error['message'] as String? ?? 'Request failed.')
            : 'Request failed.',
      );
    }
    return data ?? {};
  }

  Future<bool> tryRefresh() async {
    final refresh = await storage.getRefresh();
    if (refresh == null) return false;
    try {
      final request = await _open('POST', '/api/v1/auth/refresh/');
      final data = await _send(request, body: {'refresh': refresh});
      await storage.saveAccess(data['access'] as String);
      if (data['refresh'] is String) {
        await storage.saveRefresh(data['refresh'] as String);
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> send(String method, String path, {Object? body}) async {
    final access = await storage.getAccess();
    final request = await _open(method, path);
    try {
      return await _send(request, access: access, body: body);
    } on ApiException catch (e) {
      if (e.statusCode != 401) rethrow;
    }
    if (await tryRefresh()) {
      final retry = await _open(method, path);
      return _send(retry, access: await storage.getAccess(), body: body);
    }
    throw ApiException(401, 'Session expired. Please log in again.');
  }

  Future<Map<String, dynamic>> get(String path) => send('GET', path);

  Future<AppUser> updateProfile({String? email, String? phone}) async {
    final data = await send('PATCH', '/api/v1/me/', body: {
      'email': email ?? '',
      'phone': phone ?? '',
    });
    return AppUser.fromJson(data);
  }

  Future<void> removeAvatar() async {
    await send('DELETE', '/api/v1/me/avatar/');
  }

  Future<http.Response> _uploadAvatarOnce(File file, String access) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/v1/me/avatar/'));
    request.headers['Authorization'] = 'Bearer $access';
    request.files.add(await http.MultipartFile.fromPath('avatar', file.path));
    final streamed = await request.send().timeout(const Duration(seconds: 30));
    return http.Response.fromStream(streamed);
  }

  Future<String?> uploadAvatar(File file) async {
    var access = await storage.getAccess() ?? '';
    var response = await _uploadAvatarOnce(file, access);
    if (response.statusCode == 401 && await tryRefresh()) {
      access = await storage.getAccess() ?? '';
      response = await _uploadAvatarOnce(file, access);
    }
    Map<String, dynamic> data = {};
    try {
      data = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {}
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error = data['error'];
      throw ApiException(
        response.statusCode,
        error is Map ? (error['message'] as String? ?? 'Upload failed.') : 'Upload failed.',
      );
    }
    return data['avatar_url'] as String?;
  }

  Future<LoginResult> login(String username, String password) async {
    final request = await _open('POST', '/api/v1/auth/login/');
    final data = await _send(request,
        body: {'username': username, 'password': password});
    final access = data['access'] as String;
    final refresh = data['refresh'] as String;
    AppUser user;
    try {
      final meRequest = await _open('GET', '/api/v1/me/');
      final meData = await _send(meRequest, access: access);
      user = AppUser.fromJson(meData);
    } catch (_) {
      user = AppUser(
          username: username, role: data['role'] as String? ?? 'student');
    }
    await storage.save(
      access: access,
      refresh: refresh,
      userJson: jsonEncode(user.toJson()),
    );
    return LoginResult(
      access: access,
      refresh: refresh,
      user: user,
      mustChangePassword: data['must_change_password'] == true,
    );
  }

  Future<void> logout() async {
    final refresh = await storage.getRefresh();
    if (refresh != null) {
      try {
        final request = await _open('POST', '/api/v1/auth/logout/');
        await _send(request,
            access: await storage.getAccess(), body: {'refresh': refresh});
      } catch (_) {}
    }
    await storage.clear();
  }

  Future<void> changePassword(
      String currentPassword, String newPassword) async {
    String? access = await storage.getAccess();
    var request = await _open('POST', '/api/v1/auth/change-password/');
    try {
      await _send(request, access: access, body: {
        'current_password': currentPassword,
        'new_password': newPassword,
      });
      return;
    } on ApiException catch (e) {
      if (e.statusCode != 401) rethrow;
    }
    if (!await tryRefresh()) {
      throw ApiException(401, 'Session expired. Please log in again.');
    }
    access = await storage.getAccess();
    request = await _open('POST', '/api/v1/auth/change-password/');
    await _send(request, access: access, body: {
      'current_password': currentPassword,
      'new_password': newPassword,
    });
  }

  Future<SemesterSummary> fetchGrades(int semester) async {
    final data = await get('/api/v1/me/grades/?semester=$semester');
    return SemesterSummary.fromJson(data);
  }
}
