// Utility functions to format data for sales-friendly display

/**
 * Converts technical signal reasons into a single professional sentence
 * Input: ["techSignals 0.90", "recentVolume 0.75", "execChanges 0.60", "sentiment 0.70", "funding 0.50"]
 * Output: "Recently raised funding, actively hiring leadership, strong technology adoption activity."
 */
export function formatBuyingSignals(reasons: string[]): string {
  const signals: string[] = [];
  const signalData: Record<string, number> = {};

  // Parse all signals
  reasons.forEach(reason => {
    const [type, valueStr] = reason.split(' ');
    signalData[type] = parseFloat(valueStr);
  });

  // Build sentence from strongest signals (>= 0.4 threshold)
  if (signalData.funding >= 0.4) {
    signals.push('recently raised funding');
  }

  if (signalData.execChanges >= 0.4) {
    signals.push('actively hiring leadership');
  }

  if (signalData.techSignals >= 0.6) {
    signals.push('strong technology adoption activity');
  } else if (signalData.techSignals >= 0.4) {
    signals.push('technology stack expansion');
  }

  if (signalData.recentVolume >= 0.6) {
    signals.push('high market visibility');
  }

  // Fallback if no strong signals
  if (signals.length === 0) {
    return 'Company shows relevant buying signals based on recent activity.';
  }

  // Capitalize first letter and add period
  const sentence = signals.join(', ');
  return sentence.charAt(0).toUpperCase() + sentence.slice(1) + '.';
}

/**
 * Formats detailed buying signals with percentages
 */
export function formatDetailedSignals(reasons: string[]): Array<{
  label: string;
  value: number;
  description: string;
}> {
  const details: Array<{ label: string; value: number; description: string }> = [];

  reasons.forEach(reason => {
    const [type, valueStr] = reason.split(' ');
    const value = Math.round(parseFloat(valueStr) * 100);

    switch (type) {
      case 'techSignals':
        details.push({
          label: 'Technology Signals',
          value,
          description: 'Technology adoption, stack changes, infrastructure updates',
        });
        break;
      case 'recentVolume':
        details.push({
          label: 'Activity Level',
          value,
          description: 'Recent announcements, posts, and public activity',
        });
        break;
      case 'execChanges':
        details.push({
          label: 'Leadership',
          value,
          description: 'Executive changes, new hires, team expansion',
        });
        break;
      case 'sentiment':
        details.push({
          label: 'Sentiment',
          value,
          description: 'Overall positive sentiment in public communications',
        });
        break;
      case 'funding':
        details.push({
          label: 'Funding',
          value,
          description: 'Fundraising announcements, investment activity',
        });
        break;
    }
  });

  return details;
}

/**
 * Get a simple emoji-based summary
 */
export function getSignalsSummary(reasons: string[]): string {
  const categories = new Set<string>();

  reasons.forEach(reason => {
    const [type, valueStr] = reason.split(' ');
    const value = parseFloat(valueStr);

    if (value > 0.3) {
      switch (type) {
        case 'techSignals':
          categories.add('🔥 Tech');
          break;
        case 'recentVolume':
          categories.add('📊 Active');
          break;
        case 'execChanges':
          categories.add('👔 Hiring');
          break;
        case 'sentiment':
          if (value >= 0.6) categories.add('✅ Positive');
          break;
        case 'funding':
          categories.add('💰 Funded');
          break;
      }
    }
  });

  return Array.from(categories).join(' • ') || 'Buying signals detected';
}
