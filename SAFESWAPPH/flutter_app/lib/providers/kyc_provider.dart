import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/kyc_model.dart';
import '../services/upload_service.dart';

class KYCProvider extends ChangeNotifier {
  static const _storage = FlutterSecureStorage();
  static const _baseUrl = 'http://10.0.2.2:8000/api';

  KYCModel? _kyc;
  bool _isLoading = false;
  String? _errorMessage;

  KYCModel? get kyc => _kyc;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  String get kycStatus {
    if (_kyc == null) return 'not_submitted';
    return _kyc!.status;
  }

  bool get isKycApproved => _kyc?.isApproved ?? false;

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

  void _setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  void _clearError() {
    _errorMessage = null;
  }

  Future<void> fetchKYCStatus() async {
    _isLoading = true;
    _clearError();
    notifyListeners();

    try {
      final response = await http
          .get(
            Uri.parse('$_baseUrl/kyc/status/'),
            headers: await _authHeaders(),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        if (body['status'] == 'not_submitted') {
          _kyc = null;
        } else {
          _kyc = KYCModel.fromJson(body);
        }
      } else {
        _kyc = null;
      }
    } catch (e) {
      _kyc = null;
      _setError('Failed to load KYC status: $e');
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<String> uploadImage({
    required File imageFile,
    void Function(double percent)? onProgress,
  }) async {
    return UploadService.uploadImage(
      imageFile: imageFile,
      onProgress: onProgress,
    );
  }

  Future<bool> submitKYC({
    required String fullLegalName,
    required String idType,
    required String idPhotoUrl,
    required String selfieUrl,
  }) async {
    _isLoading = true;
    _clearError();
    notifyListeners();

    try {
      final body = jsonEncode({
        'full_legal_name': fullLegalName,
        'id_type': idType,
        'id_photo_url': idPhotoUrl,
        'selfie_url': selfieUrl,
      });

      final response = await http
          .post(
            Uri.parse('$_baseUrl/kyc/submit/'),
            headers: await _authHeaders(),
            body: body,
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 201) {
        await fetchKYCStatus();
        return true;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      _setError(data['error'] as String? ?? 'KYC submission failed');
      return false;
    } catch (e) {
      _setError('Network error: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
