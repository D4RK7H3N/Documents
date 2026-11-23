import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/app_state.dart';
import '../../data/api_client.dart';
import '../../domain/models.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _semester = 1;
  SemesterSummary? _summary;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final state = context.read<AppState>();
    try {
      final summary = await state.api.fetchGrades(_semester);
      if (!mounted) return;
      setState(() {
        _summary = summary;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (e.statusCode == 401 && mounted) {
        await state.logout();
        return;
      }
      if (mounted) {
        setState(() {
          _error = e.message;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _error = 'Network error. Pull down to retry.';
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Grades'),
        actions: [
          if (!_loading)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _load,
              tooltip: 'Refresh',
            ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 1, label: Text('Semester 1')),
                  ButtonSegment(value: 2, label: Text('Semester 2')),
                ],
                selected: {_semester},
                onSelectionChanged: (set) {
                  setState(() => _semester = set.first);
                  _load();
                },
              ),
              const SizedBox(height: 16),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null)
                _ErrorCard(message: _error!, onRetry: _load)
              else
                ..._buildContent(context, _summary),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _buildContent(BuildContext context, SemesterSummary? summary) {
    if (summary == null) return [];
    return [
      Text(
        'Last updated: ${summary.lastUpdatedText}',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
      ),
      const SizedBox(height: 12),
      Card(
        elevation: 0,
        color: Theme.of(context).colorScheme.primaryContainer,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.workspace_premium_outlined,
                  size: 44,
                  color: Theme.of(context).colorScheme.onPrimaryContainer),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'General Average',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                        color: Theme.of(context)
                            .colorScheme
                            .onPrimaryContainer
                            .withAlpha(190),
                      ),
                    ),
                    Text(
                      summary.generalAverage?.toString() ?? 'Incomplete',
                      style: TextStyle(
                        fontSize: 34,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -1.2,
                        color: summary.generalAverage == null
                            ? Theme.of(context)
                                .colorScheme
                                .onPrimaryContainer
                                .withAlpha(115)
                            : Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 16),
      if (summary.subjects.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 32),
          child: Center(child: Text('No subjects assigned yet.')),
        )
      else
        ...summary.subjects.map((s) => _SubjectCard(subject: s)),
    ];
  }
}

class _SubjectCard extends StatelessWidget {
  final SubjectGrade subject;

  const _SubjectCard({required this.subject});

  String? _gradeLabel(int? value) => value?.toString();

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Expanded(
              child: Text(
                subject.subject,
                style:
                    const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
              ),
            ),
            _GradeChip(label: 'Q1', value: _gradeLabel(subject.q1)),
            const SizedBox(width: 8),
            _GradeChip(label: 'Q2', value: _gradeLabel(subject.q2)),
            const SizedBox(width: 8),
            _GradeChip(
                label: 'Final',
                value: _gradeLabel(subject.finalGrade),
                emphasized: true),
          ],
        ),
      ),
    );
  }
}

class _GradeChip extends StatelessWidget {
  final String label;
  final String? value;
  final bool emphasized;

  const _GradeChip(
      {required this.label, required this.value, this.emphasized = false});

  @override
  Widget build(BuildContext context) {
    final shown = value ?? '—';
    final filled = value != null;
    return Container(
      width: emphasized ? 56 : 44,
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        color: !filled
            ? Theme.of(context).colorScheme.surfaceContainerHigh
            : (emphasized
                ? Theme.of(context).colorScheme.primary
                : Theme.of(context).colorScheme.secondaryContainer),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: emphasized && filled
                  ? Colors.white70
                  : Theme.of(context).colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w500,
            ),
          ),
          Text(
            shown,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: emphasized && filled
                  ? Colors.white
                  : (filled
                      ? Theme.of(context).colorScheme.onSurface
                      : Theme.of(context)
                          .colorScheme
                          .onSurfaceVariant
                          .withAlpha(150)),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorCard({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.wifi_off_outlined,
              size: 48, color: Theme.of(context).colorScheme.onSurfaceVariant),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}
