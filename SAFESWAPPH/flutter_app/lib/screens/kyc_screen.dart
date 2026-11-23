import 'dart:io';

import 'package:dotted_border/dotted_border.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../providers/kyc_provider.dart';

class KYCScreen extends StatefulWidget {
  const KYCScreen({super.key});

  @override
  State<KYCScreen> createState() => _KYCScreenState();
}

class _KYCScreenState extends State<KYCScreen> {
  final _pageController = PageController();
  int _currentStep = 0;

  final _nameController = TextEditingController();
  String _selectedIdType = 'philsys';
  File? _idPhotoFile;
  File? _selfieFile;
  String? _idPhotoUrl;
  String? _selfieUrl;
  bool _idPhotoUploading = false;
  bool _selfieUploading = false;
  double _idPhotoProgress = 0;
  double _selfieProgress = 0;
  bool _confirmCheckbox = false;
  bool _isSubmitting = false;

  static const _idTypes = [
    {'value': 'philsys', 'label': 'PhilSys National ID'},
    {'value': 'drivers_license', 'label': "Driver's License"},
    {'value': 'passport', 'label': 'Passport'},
    {'value': 'umid', 'label': 'UMID'},
    {'value': 'sss', 'label': 'SSS ID'},
    {'value': 'voters_id', 'label': "Voter's ID"},
  ];

  @override
  void dispose() {
    _pageController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  bool get _step1Valid => _nameController.text.trim().isNotEmpty;

  bool get _step2Valid =>
      _idPhotoUrl != null &&
      _selfieUrl != null &&
      !_idPhotoUploading &&
      !_selfieUploading;

  bool get _step3Valid => _step1Valid && _step2Valid && _confirmCheckbox;

  Future<void> _pickImage({required bool isIdPhoto}) async {
    final source = await showDialog<ImageSource>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Choose source'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Camera'),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Gallery'),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null) return;

    final picker = ImagePicker();
    final picked = await picker.pickImage(source: source, maxWidth: 1920);
    if (picked == null) return;

    final file = File(picked.path);
    setState(() {
      if (isIdPhoto) {
        _idPhotoFile = file;
        _idPhotoUrl = null;
        _idPhotoProgress = 0;
      } else {
        _selfieFile = file;
        _selfieUrl = null;
        _selfieProgress = 0;
      }
    });

    await _uploadToR2(file, isIdPhoto: isIdPhoto);
  }

  Future<void> _uploadToR2(File file, {required bool isIdPhoto}) async {
    final provider = context.read<KYCProvider>();

    setState(() {
      if (isIdPhoto) {
        _idPhotoUploading = true;
      } else {
        _selfieUploading = true;
      }
    });

    try {
      final url = await provider.uploadImage(
        imageFile: file,
        onProgress: (p) {
          setState(() {
            if (isIdPhoto) {
              _idPhotoProgress = p;
            } else {
              _selfieProgress = p;
            }
          });
        },
      );
      setState(() {
        if (isIdPhoto) {
          _idPhotoUrl = url;
          _idPhotoUploading = false;
          _idPhotoProgress = 1.0;
        } else {
          _selfieUrl = url;
          _selfieUploading = false;
          _selfieProgress = 1.0;
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
      setState(() {
        if (isIdPhoto) {
          _idPhotoUploading = false;
          _idPhotoFile = null;
        } else {
          _selfieUploading = false;
          _selfieFile = null;
        }
      });
    }
  }

  Future<void> _submitKYC() async {
    if (!_step3Valid) return;

    setState(() => _isSubmitting = true);

    final provider = context.read<KYCProvider>();
    final success = await provider.submitKYC(
      fullLegalName: _nameController.text.trim(),
      idType: _selectedIdType,
      idPhotoUrl: _idPhotoUrl!,
      selfieUrl: _selfieUrl!,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (success) {
      await showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green, size: 28),
              SizedBox(width: 12),
              Text('Submitted!'),
            ],
          ),
          content: const Text(
            'Your KYC verification has been submitted. '
            'An admin will review it shortly.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                Navigator.pop(context);
              },
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } else {
      final err = provider.errorMessage ?? 'Submission failed';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: Colors.red),
      );
    }
  }

  void _goToStep(int step) {
    _pageController.animateToPage(
      step,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('KYC Verification'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (_currentStep > 0) {
              _goToStep(_currentStep - 1);
            } else {
              Navigator.pop(context);
            }
          },
        ),
      ),
      body: _isSubmitting
          ? const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Submitting your KYC...'),
                ],
              ),
            )
          : Column(
              children: [
                _buildStepIndicator(),
                Expanded(
                  child: PageView(
                    controller: _pageController,
                    physics: const NeverScrollableScrollPhysics(),
                    onPageChanged: (i) => setState(() => _currentStep = i),
                    children: [
                      _buildStep1(),
                      _buildStep2(),
                      _buildStep3(),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildStepIndicator() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: List.generate(3, (i) {
          final isActive = i == _currentStep;
          final isDone = i < _currentStep;
          return Expanded(
            child: Row(
              children: [
                if (i > 0)
                  Expanded(
                    child: Container(
                      height: 2,
                      color: isDone
                          ? const Color(0xFF185FA5)
                          : Colors.grey.shade300,
                    ),
                  ),
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isDone || isActive
                        ? const Color(0xFF185FA5)
                        : Colors.grey.shade300,
                  ),
                  child: Center(
                    child: isDone
                        ? const Icon(Icons.check, color: Colors.white, size: 18)
                        : Text(
                            '${i + 1}',
                            style: TextStyle(
                              color: isActive
                                  ? Colors.white
                                  : Colors.grey.shade600,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          );
        }),
      ),
    );
  }

  Widget _buildStep1() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Step 1 of 3: Personal Info',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Full Legal Name',
              hintText: 'Enter your full name as shown on your ID',
              prefixIcon: Icon(Icons.person),
            ),
            textCapitalization: TextCapitalization.words,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 20),
          DropdownButtonFormField<String>(
            initialValue: _selectedIdType,
            decoration: const InputDecoration(
              labelText: 'ID Type',
              prefixIcon: Icon(Icons.badge),
            ),
            items: _idTypes.map((t) {
              return DropdownMenuItem(
                value: t['value'],
                child: Text(t['label']!),
              );
            }).toList(),
            onChanged: (v) {
              if (v != null) setState(() => _selectedIdType = v);
            },
          ),
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: _step1Valid ? () => _goToStep(1) : null,
            child: const Text('Next'),
          ),
        ],
      ),
    );
  }

  Widget _buildStep2() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Step 2 of 3: Upload Documents',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 24),
          _buildUploadBox(
            label: 'Government ID',
            file: _idPhotoFile,
            isUploading: _idPhotoUploading,
            progress: _idPhotoProgress,
            uploadedUrl: _idPhotoUrl,
            isIdPhoto: true,
          ),
          const SizedBox(height: 16),
          _buildUploadBox(
            label: 'Selfie with ID',
            file: _selfieFile,
            isUploading: _selfieUploading,
            progress: _selfieProgress,
            uploadedUrl: _selfieUrl,
            isIdPhoto: false,
            helperText: 'Take a selfie holding your ID next to your face',
          ),
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: _step2Valid ? () => _goToStep(2) : null,
            child: const Text('Next'),
          ),
        ],
      ),
    );
  }

  Widget _buildUploadBox({
    required String label,
    File? file,
    required bool isUploading,
    required double progress,
    String? uploadedUrl,
    required bool isIdPhoto,
    String? helperText,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        if (helperText != null)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Text(
              helperText,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: isUploading ? null : () => _pickImage(isIdPhoto: isIdPhoto),
          child: DottedBorder(
            borderType: BorderType.RRect,
            radius: const Radius.circular(12),
            color: uploadedUrl != null ? Colors.green : Colors.grey.shade400,
            dashPattern: const [6, 3],
            child: Container(
              width: double.infinity,
              height: 180,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                color: Colors.grey.shade50,
              ),
              child: _buildUploadContent(
                file: file,
                isUploading: isUploading,
                progress: progress,
                uploadedUrl: uploadedUrl,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildUploadContent({
    File? file,
    required bool isUploading,
    required double progress,
    String? uploadedUrl,
  }) {
    if (isUploading) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 40,
            height: 40,
            child: CircularProgressIndicator(
              value: progress > 0 ? progress : null,
              strokeWidth: 3,
              color: const Color(0xFF185FA5),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            progress > 0
                ? 'Uploading ${(progress * 100).toInt()}%'
                : 'Uploading...',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          if (progress > 0)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: LinearProgressIndicator(
                value: progress,
                backgroundColor: Colors.grey.shade200,
                color: const Color(0xFF185FA5),
              ),
            ),
        ],
      );
    }

    if (uploadedUrl != null) {
      return Stack(
        alignment: Alignment.center,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: file != null
                ? Image.file(file,
                    fit: BoxFit.cover, width: double.infinity, height: 180)
                : const SizedBox.shrink(),
          ),
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.green,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check, color: Colors.white, size: 18),
            ),
          ),
        ],
      );
    }

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.cloud_upload_outlined,
            size: 40, color: Colors.grey.shade400),
        const SizedBox(height: 8),
        Text(
          'Tap to upload',
          style: TextStyle(
              color: Colors.grey.shade600, fontWeight: FontWeight.w500),
        ),
      ],
    );
  }

  Widget _buildStep3() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Step 3 of 3: Review & Submit',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 24),
          _buildSummaryRow('Full Name', _nameController.text.trim()),
          const Divider(height: 24),
          _buildSummaryRow(
            'ID Type',
            _idTypes.firstWhere((t) => t['value'] == _selectedIdType)['label']!,
          ),
          const Divider(height: 24),
          const Text('ID Photo', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          if (_idPhotoFile != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(
                _idPhotoFile!,
                height: 120,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
          const SizedBox(height: 16),
          const Text('Selfie with ID',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          if (_selfieFile != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(
                _selfieFile!,
                height: 120,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
          const SizedBox(height: 24),
          CheckboxListTile(
            value: _confirmCheckbox,
            onChanged: (v) => setState(() => _confirmCheckbox = v ?? false),
            title: const Text(
              'I confirm all information is accurate and this is my real identity',
              style: TextStyle(fontSize: 14),
            ),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _step3Valid ? _submitKYC : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0F6E56),
            ),
            child: const Text('Submit KYC'),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 100,
          child: Text(
            label,
            style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
          ),
        ),
        Expanded(
          child:
              Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ),
      ],
    );
  }
}
