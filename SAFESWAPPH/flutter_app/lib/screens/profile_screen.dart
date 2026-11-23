import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/kyc_provider.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<KYCProvider>().fetchKYCStatus();
    });
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'not_submitted':
        return Colors.grey;
      case 'pending':
        return Colors.amber.shade700;
      case 'approved':
        return Colors.green;
      case 'rejected':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'not_submitted':
        return 'Not Submitted';
      case 'pending':
        return 'Under Review';
      case 'approved':
        return 'Verified ✓';
      case 'rejected':
        return 'Rejected';
      default:
        return status;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'not_submitted':
        return Icons.verified_user_outlined;
      case 'pending':
        return Icons.hourglass_top;
      case 'approved':
        return Icons.verified_user;
      case 'rejected':
        return Icons.cancel_outlined;
      default:
        return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final kycProvider = context.watch<KYCProvider>();
    final status = kycProvider.kycStatus;
    final kyc = kycProvider.kyc;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const CircleAvatar(
              radius: 40,
              backgroundColor: Color(0xFF185FA5),
              child: Icon(Icons.person, size: 40, color: Colors.white),
            ),
            const SizedBox(height: 16),
            const Text(
              'User Name',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              '+63 9XX XXX XXXX',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
            ),
            const SizedBox(height: 32),
            const Text(
              'KYC Verification',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: _statusColor(status).withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        _statusIcon(status),
                        color: _statusColor(status),
                        size: 28,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: _statusColor(status).withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              _statusLabel(status),
                              style: TextStyle(
                                color: _statusColor(status),
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          if (status == 'rejected' &&
                              kyc?.rejectionReason != null &&
                              kyc!.rejectionReason.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                'Reason: ${kyc.rejectionReason}',
                                style: const TextStyle(
                                  color: Colors.red,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    if (status == 'not_submitted' || status == 'rejected')
                      TextButton(
                        onPressed: () =>
                            Navigator.pushNamed(context, '/kyc'),
                        child: Text(
                          status == 'rejected' ? 'Resubmit' : 'Start KYC',
                          style: const TextStyle(
                            color: Color(0xFF185FA5),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
