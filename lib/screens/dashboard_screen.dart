import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'package:fl_chart/fl_chart.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _api = ApiService();
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _api.fetchDashboard();
      setState(() => _data = data);
    } catch (e) {
      // ignore
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_data == null) {
      return Center(
        child: ElevatedButton(onPressed: _load, child: const Text('Retry')),
      );
    }

    final allTime = _data!['all_time'];
    final month = _data!['current_month'];
    final trend = _data!['monthly_trend'] as List;
    final categories = _data!['category_spending'] as List;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Overview', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _Card('All Time Net', allTime['net'], Colors.indigo)),
              const SizedBox(width: 12),
              Expanded(child: _Card('Month Net', month['net'], Colors.teal)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _Card('All Credits', allTime['credits'], Colors.green)),
              const SizedBox(width: 12),
              Expanded(child: _Card('All Debits', allTime['debits'], Colors.red)),
            ],
          ),
          const SizedBox(height: 24),
          Text('6-Month Trend', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          SizedBox(
            height: 200,
            child: BarChart(
              BarChartData(
                barGroups: [
                  for (int i = 0; i < trend.length; i++)
                    BarChartGroupData(x: i, barRods: [
                      BarChartRodData(toY: double.tryParse(trend[i]['credits'].toString()) ?? 0, color: Colors.green),
                      BarChartRodData(toY: double.tryParse(trend[i]['debits'].toString()) ?? 0, color: Colors.red),
                    ]),
                ],
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (v, meta) => Text(trend[v.toInt()]['month'].toString().substring(0, 3)),
                    ),
                  ),
                  leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text('Category Spending', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          if (categories.isEmpty)
            const Text('No data')
          else
            ...categories.map((c) => ListTile(
                  title: Text(c['category']),
                  trailing: Text('₹ ${c['total']}'),
                )),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final String title;
  final String value;
  final Color color;

  const _Card(this.title, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: TextStyle(color: color)),
            const SizedBox(height: 8),
            Text('₹ $value', style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}
