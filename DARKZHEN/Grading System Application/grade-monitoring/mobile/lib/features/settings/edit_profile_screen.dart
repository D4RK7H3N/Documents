import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/app_state.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _email;
  late final TextEditingController _phone;
  final _picker = ImagePicker();
  bool _photoBusy = false;

  @override
  void initState() {
    super.initState();
    final user = context.read<AppState>().user;
    _email = TextEditingController(text: user?.email ?? '');
    _phone = TextEditingController(text: user?.phone ?? '');
  }

  @override
  void dispose() {
    _email.dispose();
    _phone.dispose();
    super.dispose();
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final state = context.read<AppState>();
    final error = await state.saveProfile(
        email: _email.text.trim(), phone: _phone.text.trim());
    if (!mounted) return;
    _showMessage(error ?? 'Profile details saved.');
  }

  Future<void> _pickPhoto() async {
    final picked = await _picker.pickImage(
        source: ImageSource.gallery, maxWidth: 1024, imageQuality: 85);
    if (picked == null || !mounted) return;
    final tooLarge = await picked.length() > 2 * 1024 * 1024;
    if (!mounted) return;
    if (tooLarge) {
      _showMessage('Photo must be smaller than 2 MB.');
      return;
    }
    setState(() => _photoBusy = true);
    final error =
        await context.read<AppState>().updateAvatarPhoto(File(picked.path));
    if (!mounted) return;
    setState(() => _photoBusy = false);
    _showMessage(error ?? 'Profile photo updated.');
  }

  Future<void> _removePhoto() async {
    setState(() => _photoBusy = true);
    final error = await context.read<AppState>().removeAvatarPhoto();
    if (!mounted) return;
    setState(() => _photoBusy = false);
    _showMessage(error ?? 'Profile photo removed.');
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final user = state.user;
    return Scaffold(
      appBar: AppBar(title: const Text('Edit profile')),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Center(
                child: CircleAvatar(
                  radius: 44,
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  foregroundColor: Colors.white,
                  backgroundImage: user?.avatarUrl != null
                      ? NetworkImage(user!.avatarUrl!)
                      : null,
                  onBackgroundImageError:
                      user?.avatarUrl != null ? (_, __) {} : null,
                  child: user?.avatarUrl == null
                      ? const Icon(Icons.person, size: 44)
                      : null,
                ),
              ),
              const SizedBox(height: 12),
              if (_photoBusy) const Center(child: CircularProgressIndicator()),
              if (!_photoBusy) ...[
                OutlinedButton.icon(
                  onPressed: state.busy ? null : _pickPhoto,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Change photo'),
                ),
                if (user?.avatarUrl != null)
                  TextButton.icon(
                    onPressed: state.busy ? null : _removePhoto,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Remove photo'),
                  ),
              ],
              const SizedBox(height: 24),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email address (optional)',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  final v = value?.trim() ?? '';
                  if (v.isEmpty) return null;
                  final valid =
                      RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v);
                  return valid ? null : 'Enter a valid email address';
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                maxLength: 32,
                decoration: const InputDecoration(
                  labelText: 'Phone number (optional)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Your name and LRN are managed by the school. Contact your adviser for corrections.',
                style: TextStyle(
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: state.busy ? null : _save,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: state.busy
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Save details'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
