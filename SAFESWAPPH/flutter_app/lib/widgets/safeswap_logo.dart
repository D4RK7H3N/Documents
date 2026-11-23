import 'package:flutter/material.dart';

class SafeSwapLogo extends StatelessWidget {
  final double size;
  final bool showText;

  const SafeSwapLogo({
    super.key,
    this.size = 100,
    this.showText = true,
  });

  @override
  Widget build(BuildContext context) {
    final iconSize = showText ? size * 0.45 : size;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: size,
          height: showText ? size * 0.5 : size,
          child: CustomPaint(
            painter: _ShieldPainter(),
            size: Size(iconSize, iconSize),
          ),
        ),
        if (showText) ...[
          SizedBox(height: size * 0.1),
          _buildText(),
        ],
      ],
    );
  }

  Widget _buildText() {
    return Column(
      children: [
        RichText(
          text: TextSpan(
            style: TextStyle(
              fontSize: size * 0.28,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
              fontFamily: 'Poppins',
            ),
            children: const <TextSpan>[
              TextSpan(
                text: 'Safe',
                style: TextStyle(color: Color(0xFF185FA5)),
              ),
              TextSpan(
                text: 'Swap',
                style: TextStyle(color: Color(0xFF534AB7)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'PHILIPPINES',
          style: TextStyle(
            fontSize: size * 0.09,
            fontWeight: FontWeight.w600,
            color: const Color(0xFF0F6E56),
            letterSpacing: 3,
            fontFamily: 'Poppins',
          ),
        ),
      ],
    );
  }
}

class _ShieldPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final shieldPath = Path()
      ..moveTo(w * 0.3, 0)
      ..lineTo(w * 0.7, 0)
      ..lineTo(w * 0.88, h * 0.55)
      ..quadraticBezierTo(w * 0.5, h, w * 0.5, h)
      ..quadraticBezierTo(w * 0.5, h, w * 0.12, h * 0.55)
      ..close();

    const gradient = LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        Color(0xFF185FA5),
        Color(0xFF3B2E8A),
        Color(0xFF534AB7),
      ],
    );

    final shadowPaint = Paint()
      ..shader = gradient.createShader(
        Rect.fromLTWH(0, 0, w, h),
      )
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, w * 0.08);

    canvas.drawPath(shieldPath, shadowPaint);

    final shieldPaint = Paint()
      ..shader = gradient.createShader(
        Rect.fromLTWH(0, 0, w, h),
      );

    canvas.drawPath(shieldPath, shieldPaint);

    final innerPath = Path()
      ..moveTo(w * 0.34, h * 0.08)
      ..lineTo(w * 0.66, h * 0.08)
      ..lineTo(w * 0.82, h * 0.52)
      ..quadraticBezierTo(w * 0.5, h * 0.9, w * 0.5, h * 0.9)
      ..quadraticBezierTo(w * 0.5, h * 0.9, w * 0.18, h * 0.52)
      ..close();

    final innerPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.02
      ..color = Colors.white.withValues(alpha: 0.15);

    canvas.drawPath(innerPath, innerPaint);

    final checkPath = Path()
      ..moveTo(w * 0.32, h * 0.48)
      ..lineTo(w * 0.44, h * 0.62)
      ..lineTo(w * 0.68, h * 0.36);

    final checkPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.07
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = Colors.white;

    canvas.drawPath(checkPath, checkPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
