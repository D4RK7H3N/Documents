import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

class PaymentScreen extends StatefulWidget {
  final int tradeId;
  final String amount;

  const PaymentScreen({
    super.key,
    required this.tradeId,
    required this.amount,
  });

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  static const _baseUrl = 'http://10.0.2.2:8000/api';
  String? _checkoutUrl;
  bool _isCreating = false;
  String? _selectedProvider;

  Future<void> _createPayment(String provider) async {
    setState(() {
      _isCreating = true;
      _selectedProvider = provider;
    });

    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/payment/create/'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'trade_id': widget.tradeId,
          'provider': provider,
        }),
      );

      if (response.statusCode == 201) {
        final body = jsonDecode(response.body);
        setState(() {
          _checkoutUrl = body['checkout_url'] as String?;
          _isCreating = false;
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(jsonDecode(response.body)['error'] ?? 'Failed')),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection error')),
        );
      }
    } finally {
      if (mounted) setState(() => _isCreating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F8FD),
      appBar: AppBar(
        title: Text('Payment',
          style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
      ),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF185FA5), Color(0xFF534AB7)],
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Color(0xFF185FA5).withValues(alpha: 0.25),
                    blurRadius: 20,
                    offset: Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Text('Amount Due',
                    style: GoogleFonts.poppins(
                      fontSize: 14,
                      color: Colors.white.withValues(alpha: 0.7),
                    )),
                  SizedBox(height: 8),
                  Text(widget.amount,
                    style: GoogleFonts.poppins(
                      fontSize: 40,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    )),
                ],
              ),
            ),
            SizedBox(height: 32),
            Text('Select Payment Method',
              style: GoogleFonts.poppins(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFF1A1A2E),
              )),
            SizedBox(height: 16),
            _buildProviderCard(
              'GCash',
              Icons.account_balance_wallet_outlined,
              Color(0xFF0F6E56),
              () => _createPayment('gcash'),
            ),
            SizedBox(height: 12),
            _buildProviderCard(
              'Maya',
              Icons.credit_card_outlined,
              Color(0xFF185FA5),
              () => _createPayment('maya'),
            ),
            if (_checkoutUrl != null) ...[
              SizedBox(height: 24),
              Container(
                width: double.infinity,
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Color(0xFFD1FAE5),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'Checkout URL generated. In production, this would open the payment page.\n\n$_checkoutUrl',
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    color: Color(0xFF065F46),
                    height: 1.5,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProviderCard(
      String name, IconData icon, Color color, VoidCallback onTap) {
    final isSelected = _selectedProvider == name.toLowerCase() && _isCreating;
    return GestureDetector(
      onTap: isSelected ? null : onTap,
      child: Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Color(0xFFE5E7EB)),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            SizedBox(width: 16),
            Expanded(
              child: Text(name,
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF1A1A2E),
                )),
            ),
            if (isSelected)
              SizedBox(
                width: 20, height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              Icon(Icons.chevron_right_rounded, color: Color(0xFF9CA3AF)),
          ],
        ),
      ),
    );
  }
}
