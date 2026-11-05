/**
 * Format a number to Indian comma system with ₹ symbol.
 * e.g. 123456.78 → ₹1,23,456.78
 */
export function formatIndianCurrency(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return '₹0.00';

  const num = Number(amount);
  const isNegative = num < 0;
  const absNum = Math.abs(num);

  const [intPart, decPart] = absNum.toFixed(2).split('.');

  // Indian grouping: last 3 digits, then groups of 2
  let result = '';
  const len = intPart.length;

  if (len <= 3) {
    result = intPart;
  } else {
    result = intPart.slice(-3);
    let remaining = intPart.slice(0, -3);
    while (remaining.length > 2) {
      result = remaining.slice(-2) + ',' + result;
      remaining = remaining.slice(0, -2);
    }
    if (remaining.length > 0) {
      result = remaining + ',' + result;
    }
  }

  return `${isNegative ? '-' : ''}₹${result}.${decPart}`;
}

/**
 * Generate and download a CSV file from data array.
 */
export function downloadCSV(data, filename) {
  if (!data || data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvRows = [
    headers.join(','),
    ...data.map(row =>
      headers.map(h => {
        const val = row[h] ?? '';
        const str = String(val);
        // Escape quotes and wrap in quotes if contains comma, quote, or newline
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    ),
  ];

  const csvString = csvRows.join('\n');
  const blob = new Blob(['\uFEFF' + csvString], { type: 'text/csv;charset=utf-8;' });

  import('file-saver').then(({ saveAs }) => {
    saveAs(blob, filename);
  });
}

/**
 * Generate and download an Excel file from data array.
 */
export function downloadExcel(data, filename) {
  if (!data || data.length === 0) return;

  import('xlsx').then((XLSX) => {
    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Transactions');

    // Auto-size columns
    const headers = Object.keys(data[0]);
    worksheet['!cols'] = headers.map(h => ({
      wch: Math.max(
        h.length,
        ...data.map(row => String(row[h] ?? '').length)
      ) + 2,
    }));

    XLSX.writeFile(workbook, filename);
  });
}
