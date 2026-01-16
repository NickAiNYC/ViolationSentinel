/**
 * ViolationSentinel JavaScript/TypeScript SDK
 * Official JavaScript client for the ViolationSentinel API
 * 
 * Installation:
 *   npm install @violationsentinel/sdk
 * 
 * Usage:
 *   import { ViolationSentinelClient } from '@violationsentinel/sdk';
 *   
 *   const client = new ViolationSentinelClient({
 *     apiKey: 'your-api-key',
 *     tenantId: 'your-tenant-id'
 *   });
 *   
 *   // List properties
 *   const properties = await client.properties.list();
 *   
 *   // Get violations
 *   const violations = await client.violations.list({ propertyId: 'prop-123' });
 */

interface ClientConfig {
  apiKey: string;
  tenantId: string;
  baseUrl?: string;
  timeout?: number;
}

interface Property {
  id: string;
  name: string;
  bbl: string;
  address?: string;
  year_built?: number;
  units?: number;
  is_monitored: boolean;
  tenant_id: string;
  created_at: string;
}

interface Violation {
  id: string;
  property_id: string;
  source: string;
  external_id: string;
  description?: string;
  violation_class?: string;
  issued_date?: string;
  resolved_date?: string;
  is_resolved: boolean;
  risk_score: number;
  confidence_score: number;
  created_at: string;
}

interface ScanRequest {
  property_ids?: string[];
  scan_all?: boolean;
  sources?: string[];
}

interface Report {
  report_id: string;
  status: string;
  download_url?: string;
  generated_at: string;
}

interface DashboardMetrics {
  total_properties: number;
  monitored_properties: number;
  total_violations: number;
  high_risk_properties: number;
  violations_last_30_days: number;
  avg_risk_score: number;
}

class ViolationSentinelError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ViolationSentinelError';
  }
}

class AuthenticationError extends ViolationSentinelError {
  constructor(message: string = 'Authentication failed') {
    super(message);
    this.name = 'AuthenticationError';
  }
}

class RateLimitError extends ViolationSentinelError {
  constructor(retryAfter: number) {
    super(`Rate limit exceeded. Retry after ${retryAfter} seconds`);
    this.name = 'RateLimitError';
  }
}

class APIError extends ViolationSentinelError {
  constructor(message: string, public statusCode: number) {
    super(message);
    this.name = 'APIError';
  }
}

export class ViolationSentinelClient {
  private apiKey: string;
  private tenantId: string;
  private baseUrl: string;
  private timeout: number;

  public properties: PropertiesAPI;
  public violations: ViolationsAPI;
  public reports: ReportsAPI;
  public webhooks: WebhooksAPI;
  public analytics: AnalyticsAPI;

  constructor(config: ClientConfig) {
    this.apiKey = config.apiKey;
    this.tenantId = config.tenantId;
    this.baseUrl = (config.baseUrl || 'https://api.violationsentinel.com').replace(/\/$/, '');
    this.timeout = config.timeout || 30000;

    this.properties = new PropertiesAPI(this);
    this.violations = new ViolationsAPI(this);
    this.reports = new ReportsAPI(this);
    this.webhooks = new WebhooksAPI(this);
    this.analytics = new AnalyticsAPI(this);
  }

  async request<T>(
    method: string,
    endpoint: string,
    options: {
      params?: Record<string, any>;
      data?: any;
    } = {}
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}/api/v1${endpoint}`);
    
    // Add query parameters
    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {
      'X-API-Key': this.apiKey,
      'X-Tenant-ID': this.tenantId,
      'Content-Type': 'application/json',
      'User-Agent': 'ViolationSentinel-JS-SDK/1.0.0'
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers,
        body: options.data ? JSON.stringify(options.data) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
        throw new RateLimitError(retryAfter);
      }

      // Handle authentication errors
      if (response.status === 401) {
        throw new AuthenticationError('Invalid API key or tenant ID');
      }

      // Handle other errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(
          errorData.detail || 'Unknown error',
          response.status
        );
      }

      // Handle no-content responses
      if (response.status === 204) {
        return undefined as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ViolationSentinelError) {
        throw error;
      }
      throw new ViolationSentinelError(`Request failed: ${error.message}`);
    }
  }
}

class PropertiesAPI {
  constructor(private client: ViolationSentinelClient) {}

  async list(skip: number = 0, limit: number = 100): Promise<Property[]> {
    return this.client.request<Property[]>('GET', '/properties', {
      params: { skip, limit }
    });
  }

  async get(propertyId: string): Promise<Property> {
    return this.client.request<Property>('GET', `/properties/${propertyId}`);
  }

  async create(data: {
    name: string;
    bbl: string;
    address?: string;
    year_built?: number;
    units?: number;
  }): Promise<Property> {
    return this.client.request<Property>('POST', '/properties', { data });
  }

  async update(propertyId: string, data: Partial<Property>): Promise<Property> {
    return this.client.request<Property>('PUT', `/properties/${propertyId}`, { data });
  }

  async delete(propertyId: string): Promise<void> {
    return this.client.request<void>('DELETE', `/properties/${propertyId}`);
  }
}

class ViolationsAPI {
  constructor(private client: ViolationSentinelClient) {}

  async list(filters: {
    property_id?: string;
    source?: string;
    is_resolved?: boolean;
    skip?: number;
    limit?: number;
  } = {}): Promise<Violation[]> {
    return this.client.request<Violation[]>('GET', '/violations', {
      params: filters
    });
  }

  async get(violationId: string): Promise<Violation> {
    return this.client.request<Violation>('GET', `/violations/${violationId}`);
  }

  async scan(request: ScanRequest): Promise<any> {
    return this.client.request('POST', '/violations/scan', { data: request });
  }
}

class ReportsAPI {
  constructor(private client: ViolationSentinelClient) {}

  async generate(data: {
    property_ids: string[];
    start_date?: string;
    end_date?: string;
    include_resolved?: boolean;
    format?: string;
  }): Promise<Report> {
    return this.client.request<Report>('POST', '/reports', { data });
  }

  async getStatus(reportId: string): Promise<Report> {
    return this.client.request<Report>('GET', `/reports/${reportId}`);
  }
}

class WebhooksAPI {
  constructor(private client: ViolationSentinelClient) {}

  async list(): Promise<any[]> {
    return this.client.request<any[]>('GET', '/webhooks');
  }

  async create(data: {
    url: string;
    events: string[];
    is_active?: boolean;
  }): Promise<any> {
    return this.client.request('POST', '/webhooks', { data });
  }

  async delete(webhookId: string): Promise<void> {
    return this.client.request<void>('DELETE', `/webhooks/${webhookId}`);
  }
}

class AnalyticsAPI {
  constructor(private client: ViolationSentinelClient) {}

  async dashboard(): Promise<DashboardMetrics> {
    return this.client.request<DashboardMetrics>('GET', '/analytics/dashboard');
  }

  async violationStats(): Promise<any> {
    return this.client.request('GET', '/analytics/violations/stats');
  }
}

// Example usage
export default async function example() {
  const client = new ViolationSentinelClient({
    apiKey: 'your-api-key',
    tenantId: 'your-tenant-id'
  });

  // List properties
  const properties = await client.properties.list();
  console.log(`Found ${properties.length} properties`);

  // Create property
  const newProperty = await client.properties.create({
    name: '123 Main Street',
    bbl: '1012650001',
    address: '123 Main St, New York, NY 10001',
    year_built: 1950,
    units: 24
  });
  console.log(`Created property: ${newProperty.id}`);

  // Get violations
  const violations = await client.violations.list({
    property_id: newProperty.id,
    is_resolved: false
  });
  console.log(`Found ${violations.length} open violations`);

  // Trigger scan
  const scanResult = await client.violations.scan({
    property_ids: [newProperty.id],
    sources: ['DOB', 'HPD', '311']
  });
  console.log(`Scan started: ${scanResult.scan_id}`);

  // Get dashboard metrics
  const metrics = await client.analytics.dashboard();
  console.log(`Total violations: ${metrics.total_violations}`);
}
