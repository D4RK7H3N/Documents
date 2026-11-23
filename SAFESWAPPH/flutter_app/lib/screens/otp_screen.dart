import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

import '../widgets/gradient_button.dart';

class OTPScreen extends StatefulWidget {
  const OTPScreen({super.key});

  @override
  State<OTPScreen> createState() => _OTPScreenState();
}

class _OTPScreenState extends State<OTPScreen> {
  static const _baseUrl = 'http://10.0.2.2:8000/api';

  late String _phoneNumber;
  final _controllers = List.generate(6, (_) => TextEditingController());
  final _focusNodes = List.generate(6, (_) => FocusNode());
  int _countdown = 300;
  Timer? _timer;
  bool _canResend = false;
  bool _isLoading = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _phoneNumber = ModalRoute.of(context)?.settings.arguments as String? ?? '';
    _startCountdown();
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _controllers) {
      c.dispose();
    }
    for (final f in _focusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  void _startCountdown() {
    _timer?.cancel();
    setState(() {
      _countdown = 300;
      _canResend = false;
    });
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      setState(() {
        _countdown--;
        if (_countdown <= 0) {
          t.cancel();
          _canResend = true;
        }
      });
    });
  }

  String get _otp {
    return _controllers.map((c) => c.text).join();
  }

  bool get _isComplete => _otp.length == 6;

  void _onDigitChanged(int index, String value) {
    if (value.isNotEmpty && index < 5) {
      _focusNodes[index + 1].requestFocus();
    }
    if (_isComplete) {
      _verifyOtp();
    }
    setState(() {});
  }

  Future<void> _verifyOtp() async {
    setState(() => _isLoading = true);

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/verify-otp/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'phone_number': _phoneNumber,
              'otp': _otp,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (!mounted) return;

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        const storage = FlutterSecureStorage();
        await storage.write(key: 'access_token', value: data['access'] as String);
        await storage.write(key: 'refresh_token', value: data['refresh'] as String);

        Navigator.pushNamedAndRemoveUntil(context, '/kyc-required', (_) => false);
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(data['error'] as String? ?? 'Verification failed'),
            backgroundColor: const Color(0xFFC0392B),
          ),
        );
        for (var c in _controllers) {
          c.clear();
        }
        _focusNodes[0].requestFocus();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Network error: $e'),
          backgroundColor: const Color(0xFFC0392B),
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _resendOtp() async {
    setState(() => _isLoading = true);

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/register/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'phone_number': _phoneNumber}),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 201) {
        for (var c in _controllers) {
          c.clear();
        }
        _focusNodes[0].requestFocus();
        _startCountdown();
      }
    } catch (_) {}

    if (mounted) setState(() => _isLoading = false);
  }

  String get _formattedTime {
    final min = (_countdown ~/ 60).toString().padLeft(2, '0');
    final sec = (_countdown % 60).toString().padLeft(2, '0');
    return '$min:$sec';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 32),
            Container(
              width: 80,
              height: 80,
              decoration: const BoxDecoration(
                color: Color(0xFF185FA5),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.sms_outlined,
                color: Colors.white,
                size: 40,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Verify Phone',
              style: GoogleFonts.poppins(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1A1A2E),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Enter the 6-digit code sent to $_phoneNumber',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 14,
                color: const Color(0xFF6B7280),
              ),
            ),
            const SizedBox(height: 40),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(6, (i) {
                return SizedBox(
                  width: 52,
                  height: 60,
                  child: TextField(
                    controller: _controllers[i],
                    focusNode: _focusNodes[i],
                    textAlign: TextAlign.center,
                    keyboardType: TextInputType.number,
                    maxLength: 1,
                    style: GoogleFonts.poppins(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF1A1A2E),
                    ),
                    decoration: InputDecoration(
                      counterText: '',
                      filled: true,
                      fillColor: const Color(0xFFF4F8FD),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: _controllers[i].text.isNotEmpty
                              ? const Color(0xFF185FA5)
                              : const Color(0xFFE5E7EB),
                          width: _controllers[i].text.isNotEmpty ? 2 : 1,
                        ),
                      ),
                    ),
                    onChanged: (v) => _onDigitChanged(i, v),
                  ),
                );
              }),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: 80,
              height: 80,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 80,
                    height: 80,
                    child: CircularProgressIndicator(
                      value: _countdown / 300,
                      strokeWidth: 4,
                      color: const Color(0xFF185FA5),
                      backgroundColor: const Color(0xFFE5E7EB),
                    ),
                  ),
                  Text(
                    _formattedTime,
                    style: GoogleFonts.poppins(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: const Color(0xFF1A1A2E),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  "Didn't receive code? ",
                  style: GoogleFonts.poppins(
                    fontSize: 13,
                    color: const Color(0xFF6B7280),
                  ),
                ),
                GestureDetector(
                  onTap: _canResend && !_isLoading ? _resendOtp : null,
                  child: Text(
                    'Resend',
                    style: GoogleFonts.poppins(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: _canResend
                          ? const Color(0xFF185FA5)
                          : const Color(0xFF6B7280),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),
            GradientButton(
              label: 'Verify',
              onPressed: _isComplete && !_isLoading ? _verifyOtp : null,
              isLoading: _isLoading,
            ),
          ],
        ),
      ),
    );
  }
}
