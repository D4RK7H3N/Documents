class KYCModel {
  final int? id;
  final int? userId;
  final String fullLegalName;
  final String idType;
  final String idPhotoUrl;
  final String selfieUrl;
  final String status;
  final String rejectionReason;
  final String? submittedAt;
  final String? reviewedAt;

  KYCModel({
    this.id,
    this.userId,
    required this.fullLegalName,
    required this.idType,
    required this.idPhotoUrl,
    required this.selfieUrl,
    required this.status,
    this.rejectionReason = '',
    this.submittedAt,
    this.reviewedAt,
  });

  bool get isApproved => status == 'approved';
  bool get isPending => status == 'pending';
  bool get isRejected => status == 'rejected';
  bool get isSubmitted => status != 'not_submitted';

  factory KYCModel.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>?;
    return KYCModel(
      id: json['id'] as int?,
      userId: user?['id'] as int?,
      fullLegalName: json['full_legal_name'] as String? ?? '',
      idType: json['id_type'] as String? ?? '',
      idPhotoUrl: json['id_photo_url'] as String? ?? '',
      selfieUrl: json['selfie_url'] as String? ?? '',
      status: json['status'] as String? ?? 'not_submitted',
      rejectionReason: json['rejection_reason'] as String? ?? '',
      submittedAt: json['submitted_at'] as String?,
      reviewedAt: json['reviewed_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'full_legal_name': fullLegalName,
      'id_type': idType,
      'id_photo_url': idPhotoUrl,
      'selfie_url': selfieUrl,
    };
  }
}
