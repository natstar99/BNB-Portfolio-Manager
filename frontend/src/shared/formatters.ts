export const formatCurrency = (value: number, currency = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

export const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00%';
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
};

export const formatDate = (dateString: string, options?: { 
  includeYear?: boolean 
}): string => {
  const dateOptions: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
  };
  
  if (options?.includeYear) {
    dateOptions.year = 'numeric';
  }
  
  return new Date(dateString).toLocaleDateString('en-US', dateOptions);
};

export const formatDateWithYear = (dateString: string): string => {
  return formatDate(dateString, { includeYear: true });
};

export const formatCurrencyForChart = (value: number, currency = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

export const formatDateForChart = (dateString: string, timePeriod?: '30D' | '1Y' | '1W' | '1D' | 'ALL'): string => {
  const date = new Date(dateString);
  
  // For longer periods (1Y and ALL), include the year to avoid confusion
  if (timePeriod === '1Y' || timePeriod === 'ALL') {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }
  
  // For shorter periods, just month and day is fine
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
};