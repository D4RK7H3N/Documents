import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  static const _baseUrl = 'http://10.0.2.2:8000/api';
  final _pageController = PageController();
  int _currentPage = 0;

  final _pages = [
    _OnboardingPage(
      icon: Icons.shield_rounded,
      title: 'Secure Escrow Trading',
      description:
          'SafeSwap PH protects both buyers and sellers. '
          'When you buy, your payment is held in escrow. '
          'The seller only gets paid once you confirm delivery.',
      gradientColors: [Color(0xFF185FA5), Color(0xFF3B2E8A)],
    ),
    _OnboardingPage(
      icon: Icons.chat_bubble_outline_rounded,
      title: 'Message Your Trader',
      description:
          'Use in-app messaging to coordinate delivery. '
          'Never share phone numbers or payment details outside '
          'the platform — it voids our dispute protection.',
      gradientColors: [Color(0xFF534AB7), Color(0xFF7C3AED)],
    ),
    _OnboardingPage(
      icon: Icons.payments_outlined,
      title: 'Pay with GCash or Maya',
      description:
          'Pay securely using GCash or Maya via our integrated '
          'payment gateway. Funds are held in escrow until you '
          'confirm you received what you paid for.',
      gradientColors: [Color(0xFF0F6E56), Color(0xFF185FA5)],
    ),
    _OnboardingPage(
      icon: Icons.report_problem_outlined,
      title: 'Something Went Wrong?',
      description:
          'If a seller doesn\'t deliver or the account doesn\'t '
          'match the listing, open a dispute. Our middlemen review '
          'evidence and resolve the case fairly.',
      gradientColors: [Color(0xFFB45309), Color(0xFFDC2626)],
    ),
  ];

  Future<void> _markSeen() async {
    final auth = context.read<AuthProvider>();
    final token = auth.accessToken;
    if (token == null) return;
    try {
      await http.post(
        Uri.parse('$_baseUrl/onboarding/done/'),
        headers: {'Authorization': 'Bearer $token'},
      );
    } catch (_) {}
  }

  void _skip() async {
    await _markSeen();
    if (mounted) Navigator.pop(context);
  }

  void _next() async {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    } else {
      await _markSeen();
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: TextButton(
                onPressed: _skip,
                child: Text('Skip',
                  style: GoogleFonts.poppins(
                    color: Color(0xFF6B7280),
                    fontWeight: FontWeight.w500,
                  )),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (i) => setState(() => _currentPage = i),
                itemCount: _pages.length,
                itemBuilder: (_, i) => _buildPage(_pages[i]),
              ),
            ),
            _buildBottomNav(),
          ],
        ),
      ),
    );
  }

  Widget _buildPage(_OnboardingPage page) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: page.gradientColors,
              ),
              borderRadius: BorderRadius.circular(32),
              boxShadow: [
                BoxShadow(
                  color: page.gradientColors[0].withValues(alpha: 0.3),
                  blurRadius: 24,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            child: Icon(page.icon, color: Colors.white, size: 56),
          ),
          SizedBox(height: 40),
          Text(
            page.title,
            style: GoogleFonts.poppins(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1A1A2E),
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 16),
          Text(
            page.description,
            style: GoogleFonts.poppins(
              fontSize: 14,
              color: Color(0xFF6B7280),
              height: 1.6,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNav() {
    return Padding(
      padding: EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(_pages.length, (i) {
              return AnimatedContainer(
                duration: Duration(milliseconds: 300),
                margin: EdgeInsets.symmetric(horizontal: 4),
                width: _currentPage == i ? 24 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: _currentPage == i
                      ? Color(0xFF185FA5)
                      : Color(0xFFE5E7EB),
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
          SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _next,
              child: Text(
                _currentPage == _pages.length - 1
                    ? 'Get Started'
                    : 'Next',
                style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OnboardingPage {
  final IconData icon;
  final String title;
  final String description;
  final List<Color> gradientColors;

  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.description,
    required this.gradientColors,
  });
}
