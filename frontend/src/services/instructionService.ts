import { request, getApiConfig } from './api';
import type { InstructionParseRequest, InstructionParseResponse, StructuredInstruction } from '../types/instruction';

/**
 * Service to interface with LLM API for natural-language instruction parsing
 * Target endpoint: POST /api/instructions/parse
 */
export async function parseInstruction(
  prompt: string,
  context?: InstructionParseRequest['context']
): Promise<StructuredInstruction> {
  const config = getApiConfig();

  // If backend is active and demo fixtures mode is explicitly disabled, call real backend
  if (!config.useDemoFixtures) {
    try {
      const response = await request<InstructionParseResponse>('/instructions/parse', {
        method: 'POST',
        body: JSON.stringify({ prompt, context }),
      });

      return {
        task: response.task,
        fields: response.fields,
        rules: response.rules,
        language: response.language || 'en',
        raw_prompt: prompt,
        parsed_at: response.timestamp || new Date().toISOString(),
      };
    } catch (err) {
      console.warn('Backend instruction parser unreachable. Falling back to local parser adapter.', err);
    }
  }

  // Local structured parser adapter for seamless client-side inspection planning
  const lower = prompt.toLowerCase();
  const fields: string[] = [];
  const rules: string[] = [];

  if (lower.includes('mrp') || lower.includes('price') || lower.includes('cost') || lower.includes('tax')) {
    fields.push('mrp', 'unit_sale_price');
    rules.push('Rule 6(1)(e) - MRP Declaration', 'Rule 6(1)(m) - Unit Sale Price');
  }

  if (lower.includes('quantity') || lower.includes('weight') || lower.includes('volume') || lower.includes('net') || lower.includes('size')) {
    fields.push('net_quantity');
    rules.push('Rule 6(1)(b) - Net Quantity', 'Rule 12 - Manner of Declaration');
  }

  if (lower.includes('manufacturer') || lower.includes('packer') || lower.includes('imported') || lower.includes('origin') || lower.includes('address')) {
    fields.push('manufacturer', 'packer', 'country_of_origin');
    rules.push('Rule 6(1)(a) - Name & Address', 'Rule 6(1)(aa) - Country of Origin');
  }

  if (lower.includes('date') || lower.includes('expiry') || lower.includes('mfg') || lower.includes('batch') || lower.includes('before')) {
    fields.push('mfg_date', 'expiry_date', 'batch_no');
    rules.push('Rule 6(1)(d) - Month & Year of Manufacture');
  }

  if (lower.includes('consumer') || lower.includes('care') || lower.includes('contact') || lower.includes('email') || lower.includes('complaint')) {
    fields.push('consumer_care');
    rules.push('Rule 6(1)(f) - Consumer Care Details');
  }

  // If general prompt, include all standard mandatory declarations
  if (fields.length === 0 || lower.includes('mandatory') || lower.includes('all') || lower.includes('compliance')) {
    fields.push('mrp', 'net_quantity', 'manufacturer', 'packer', 'mfg_date', 'country_of_origin', 'consumer_care');
    rules.push(
      'Rule 6(1)(a) - Manufacturer/Packer Address',
      'Rule 6(1)(aa) - Country of Origin',
      'Rule 6(1)(b) - Net Quantity',
      'Rule 6(1)(d) - Month & Year of Manufacture',
      'Rule 6(1)(e) - Maximum Retail Price',
      'Rule 6(1)(f) - Consumer Care Details'
    );
  }

  return {
    task: 'verify_legal_metrology_declarations',
    fields: Array.from(new Set(fields)),
    rules: Array.from(new Set(rules)),
    language: 'en',
    raw_prompt: prompt,
    extracted_keywords: prompt.split(/\s+/).filter(w => w.length > 3),
    parsed_at: new Date().toISOString(),
  };
}
