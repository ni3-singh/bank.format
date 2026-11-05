import { formatIndianCurrency } from '../utils';

const cards = [
  {
    key: 'total_dr',
    label: 'Total Debits',
    icon: '📉',
    color: 'from-rose-500/20 to-rose-600/10',
    borderColor: 'border-rose-500/30',
    textColor: 'text-rose-400',
    iconBg: 'bg-rose-500/20',
  },
  {
    key: 'total_cr',
    label: 'Total Credits',
    icon: '📈',
    color: 'from-emerald-500/20 to-emerald-600/10',
    borderColor: 'border-emerald-500/30',
    textColor: 'text-emerald-400',
    iconBg: 'bg-emerald-500/20',
  },
  {
    key: 'net_balance',
    label: 'Net Balance',
    icon: '💰',
    color: 'from-blue-500/20 to-blue-600/10',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400',
    iconBg: 'bg-blue-500/20',
  },
  {
    key: 'transaction_count',
    label: 'Transactions',
    icon: '📊',
    color: 'from-purple-500/20 to-purple-600/10',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400',
    iconBg: 'bg-purple-500/20',
  },
];

export default function SummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <section className="max-w-6xl mx-auto px-4 pb-10 animate-slide-up">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        {cards.map((card) => {
          const value = summary[card.key];
          const isCount = card.key === 'transaction_count';

          return (
            <div
              key={card.key}
              className={`
                relative overflow-hidden rounded-xl border ${card.borderColor}
                bg-gradient-to-br ${card.color} backdrop-blur-sm
                p-5 transition-all duration-300 hover:scale-[1.03] hover:shadow-lg
              `}
            >
              <div className="flex items-start justify-between mb-3">
                <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${card.iconBg} text-xl`}>
                  {card.icon}
                </span>
              </div>
              <p className="text-sm text-slate-400 mb-1">{card.label}</p>
              <p className={`text-2xl font-bold ${card.textColor}`}>
                {isCount ? value : formatIndianCurrency(value)}
              </p>
            </div>
          );
        })}
      </div>

      {/* Date range */}
      {summary.date_range && (summary.date_range.from || summary.date_range.start) && (
        <div className="mt-4 text-center text-sm text-slate-400">
          📅 Statement period: {' '}
          <span className="text-slate-300 font-medium">{summary.date_range.from || summary.date_range.start}</span>
          {' '} → {' '}
          <span className="text-slate-300 font-medium">{summary.date_range.to || summary.date_range.end}</span>
        </div>
      )}
    </section>
  );
}
