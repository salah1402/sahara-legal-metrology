/**
 * Types for LLM Natural Language Instruction Parsing
 * Target endpoint: POST /api/instructions/parse
 */

export interface StructuredInstruction {
  task: string;
  fields: string[];
  rules: string[];
  language: string;
  confidence?: number;
  extracted_keywords?: string[];
  raw_prompt?: string;
  parsed_at?: string;
}

export interface InstructionParseRequest {
  prompt: string;
  context?: {
    category?: string;
    jurisdiction?: string; // e.g. "Legal Metrology (Packaged Commodities) Rules 2011, India"
  };
}

export interface InstructionParseResponse {
  task: string;
  fields: string[];
  rules: string[];
  language: string;
  timestamp: string;
}
