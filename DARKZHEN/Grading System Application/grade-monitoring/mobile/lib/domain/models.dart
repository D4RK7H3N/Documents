import 'dart:convert';

class Student {
  final String lrn;
  final String name;
  final String section;

  Student({required this.lrn, required this.name, required this.section});

  factory Student.fromJson(Map<String, dynamic> json) => Student(
        lrn: json['lrn'] ?? '',
        name: json['name'] ?? '',
        section: json['section'] ?? '',
      );
}

class SubjectGrade {
  final String subject;
  final int? q1;
  final int? q2;
  final int? finalGrade;

  SubjectGrade({required this.subject, this.q1, this.q2, this.finalGrade});

  factory SubjectGrade.fromJson(Map<String, dynamic> json) => SubjectGrade(
        subject: json['subject'] ?? '',
        q1: json['q1'],
        q2: json['q2'],
        finalGrade: json['final'],
      );
}

class SemesterSummary {
  final int semester;
  final List<SubjectGrade> subjects;
  final int? generalAverage;
  final DateTime? lastUpdated;

  SemesterSummary({
    required this.semester,
    required this.subjects,
    this.generalAverage,
    this.lastUpdated,
  });

  factory SemesterSummary.fromJson(Map<String, dynamic> json) => SemesterSummary(
        semester: json['semester'] ?? 1,
        subjects: (json['subjects'] as List? ?? [])
            .map((e) => SubjectGrade.fromJson(e as Map<String, dynamic>))
            .toList(),
        generalAverage: json['general_average'],
        lastUpdated: json['last_updated'] != null
            ? DateTime.tryParse(json['last_updated'].toString())?.toLocal()
            : null,
      );

  String get lastUpdatedText {
    if (lastUpdated == null) return 'No grades yet';
    final local = lastUpdated!.toLocal();
    return 'Last updated ${local.day}/${local.month}/${local.year} '
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  Map<String, dynamic> toJson() => {
        'semester': semester,
        'subjects': subjects.map((s) => {'subject': s.subject, 'q1': s.q1, 'q2': s.q2, 'final': s.finalGrade}).toList(),
        'general_average': generalAverage,
        'last_updated': lastUpdated?.toIso8601String(),
      };

  static SemesterSummary fromCacheJson(Map<String, dynamic> json) {
    final subjects = (json['subjects'] as List? ?? [])
        .map((e) => SubjectGrade.fromJson(e as Map<String, dynamic>))
        .toList();
    return SemesterSummary(
      semester: json['semester'] ?? 1,
      subjects: subjects,
      generalAverage: json['general_average'],
      lastUpdated: json['last_updated'] != null ? DateTime.tryParse(json['last_updated']) : null,
    );
  }
}

class AppUser {
  final String username;
  final String role;
  final String? name;
  final String? email;
  final String? phone;
  final String? avatarUrl;

  const AppUser({
    required this.username,
    required this.role,
    this.name,
    this.email,
    this.phone,
    this.avatarUrl,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        username: json['username'] ?? '',
        role: json['role'] ?? '',
        name: json['name'],
        email: json['email'],
        phone: json['phone'],
        avatarUrl: json['avatar_url'],
      );

  Map<String, dynamic> toJson() => {
        'username': username,
        'role': role,
        'name': name,
        'email': email,
        'phone': phone,
        'avatar_url': avatarUrl,
      };

  AppUser copyWith({String? email, String? phone, String? avatarUrl, bool clearAvatar = false}) => AppUser(
        username: username,
        role: role,
        name: name,
        email: email ?? this.email,
        phone: phone ?? this.phone,
        avatarUrl: clearAvatar ? null : (avatarUrl ?? this.avatarUrl),
      );
}

String prettyJson(Map<String, dynamic> map) => jsonEncode(map);
