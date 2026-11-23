import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../widgets/gradient_button.dart';

class KYCRequiredScreen extends StatelessWidget {
  const KYCRequiredScreen({super.key});

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
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Spacer(flex: 2),
            Container(
              width: 100,
              height: 100,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF185FA5), Color(0xFF534AB7)],
                ),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.shield_outlined,
                color: Colors.white,
                size: 48,
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'Identity Verification Required',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1A1A2E),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'SafeSwap PH requires all users to verify their identity before trading',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 14,
                color: const Color(0xFF6B7280),
              ),
            ),
            const SizedBox(height: 40),
            _buildInfoRow(Icons.shield_outlined, 'Protects buyers from scammers'),
            const SizedBox(height: 16),
            _buildInfoRow(Icons.verified_user_outlined, 'Ensures seller accountability'),
            const SizedBox(height: 16),
            _buildInfoRow(Icons.gavel_outlined, 'Required by Philippine law (RA 10173)'),
            const Spacer(flex: 3),
            GradientButton(
              label: 'Verify Now',
              onPressed: () => Navigator.pushNamed(context, '/kyc'),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () =>
                  Navigator.pushNamedAndRemoveUntil(context, '/home', (_) => false),
              child: Text(
                'Do it Later',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFF6B7280),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              "You won't be able to trade until verified",
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 12,
                color: const Color(0xFFC0392B),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, color: const Color(0xFF185FA5), size: 22),
        const SizedBox(width: 16),
        Text(
          text,
          style: GoogleFonts.poppins(
            fontSize: 14,
            color: const Color(0xFF1A1A2E),
          ),
        ),
      ],
    );
  }
}
