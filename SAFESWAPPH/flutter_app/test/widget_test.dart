import 'package:flutter_test/flutter_test.dart';

import 'package:safeswapph/main.dart';

void main() {
  testWidgets('App renders welcome screen', (WidgetTester tester) async {
    await tester.pumpWidget(const SafeSwapApp());
    expect(find.text('SafeSwap PH'), findsOneWidget);
  });
}
