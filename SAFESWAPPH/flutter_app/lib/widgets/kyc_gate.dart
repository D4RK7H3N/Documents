import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/kyc_provider.dart';

class KYCGate extends StatelessWidget {
  final Widget child;
  final bool isSeller;

  const KYCGate({
    super.key,
    required this.child,
    this.isSeller = true,
  });

  @override
  Widget build(BuildContext context) {
    final kycProvider = context.watch<KYCProvider>();
    final status = kycProvider.kycStatus;

    if (!isSeller) return child;

    Widget? banner;

    if (status == 'not_submitted') {
      banner = _buildBannerStrip(
        color: Colors.grey,
        icon: Icons.verified_user_outlined,
        message: 'Complete KYC verification to start selling',
        actionLabel: 'Start KYC',
        onAction: () => Navigator.pushNamed(context, '/kyc'),
      );
    } else if (status == 'pending') {
      banner = _buildBannerStrip(
        color: Colors.amber.shade700,
        icon: Icons.hourglass_top,
        message:
            'Your KYC is under review. You will be notified once approved.',
        actionLabel: null,
      );
    } else if (status == 'rejected') {
      final reason = kycProvider.kyc?.rejectionReason ?? '';
      banner = _buildBannerStrip(
        color: Colors.red,
        icon: Icons.cancel_outlined,
        message:
            'KYC Rejected${reason.isNotEmpty ? ': $reason' : ''}',
        actionLabel: 'Resubmit',
        onAction: () => Navigator.pushNamed(context, '/kyc'),
      );
    }

    if (banner == null) return child;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        banner,
        Expanded(child: child),
      ],
    );
  }

  Widget _buildBannerStrip(
    BuildContext context, {
    required Color color,
    required IconData icon,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: color.withValues(alpha: 0.1),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: color,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          if (actionLabel != null && onAction != null)
            TextButton(
              onPressed: onAction,
              child: Text(
                actionLabel,
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
