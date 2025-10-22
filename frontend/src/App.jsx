import { useState, useEffect, useRef } from 'react';
import { FiPlus, FiSend, FiMessageSquare, FiUser, FiTrash2 } from 'react-icons/fi';
import { BsRobot } from 'react-icons/bs';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  // Form state
  const [formSaveStatus, setFormSaveStatus] = useState({}); // Track save status per message

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch sessions on component mount
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      setSessionsLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/sessions`);
      setSessions(response.data.sessions || []);
    } catch (err) {
      console.error('Error fetching sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadSession = async (sessionId) => {
    try {
      setLoading(true);
      setError(null);
      setCurrentSessionId(sessionId);

      const response = await axios.get(`${API_BASE_URL}/api/sessions/${sessionId}`);
      const sessionData = response.data;

      // Load messages
      const loadedMessages = sessionData.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
      }));

      setMessages(loadedMessages);
    } catch (err) {
      console.error('Error loading session:', err);
      setError('Failed to load session');
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation(); // Prevent triggering selectSession

    if (!window.confirm('Are you sure you want to delete this session?')) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/sessions/${sessionId}`);

      // Remove from local state
      setSessions(sessions.filter((s) => s.id !== sessionId));

      // If we deleted the current session, clear messages
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      setError('Failed to delete session');
    }
  };

  const createNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setError(null);
  };

  const selectSession = (sessionId) => {
    if (sessionId === currentSessionId) return; // Already loaded
    loadSession(sessionId);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput('');
    setError(null);

    // Add user message to UI immediately (optimistic update)
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/search`, {
        query: userQuery,
        session_id: currentSessionId,
      });

      // Update current session ID if this was a new session
      if (!currentSessionId) {
        setCurrentSessionId(response.data.session_id);
      }

      // Add assistant response
      const assistantMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.results,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Refresh sessions list to show the new/updated session
      await fetchSessions();

    } catch (err) {
      console.error('Error searching companies:', err);
      setError(
        err.response?.data?.detail ||
        'Failed to search companies. Please make sure the backend server and Temporal worker are running.'
      );
      // Remove the optimistic user message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  };

  const handleConfigSubmit = async (messageId, formData) => {
    setFormSaveStatus((prev) => ({ ...prev, [messageId]: 'saving' }));
    try {
      await axios.post(`${API_BASE_URL}/api/save-config`, {
        session_id: currentSessionId,
        configuration: formData,
      });

      // Show success status
      setFormSaveStatus((prev) => ({ ...prev, [messageId]: 'saved' }));

      // Auto-hide success message after 3 seconds
      setTimeout(() => {
        setFormSaveStatus((prev) => ({ ...prev, [messageId]: null }));
      }, 3000);
    } catch (err) {
      console.error('Error saving configuration:', err);
      setFormSaveStatus((prev) => ({ ...prev, [messageId]: 'error' }));

      // Auto-hide error message after 5 seconds
      setTimeout(() => {
        setFormSaveStatus((prev) => ({ ...prev, [messageId]: null }));
      }, 5000);
    }
  };

  const renderCompanyResults = (results, messageId) => {
    // Handle new two-stage format
    if (results.mode === 'detailed_info') {
      // Mode 2: Detailed company information
      const data = results.data;

      return (
        <div className="detailed-info">
          <h2>{data['Company name']}</h2>
          <div className="info-grid">
            <div className="info-item">
              <strong>Sector:</strong> {data.Sector}
            </div>
            <div className="info-item">
              <strong>Sub Sector:</strong> {data['Sub Sector']}
            </div>
            <div className="info-item">
              <strong>Net Worth:</strong> {data.Networth}
            </div>
            <div className="info-item">
              <strong>Employees:</strong> {data['No of Employees']}
            </div>
            <div className="info-item">
              <strong>Country of Origin:</strong> {data['Country of origin']}
            </div>
            <div className="info-item">
              <strong>Global Presence:</strong> {data['Global presence']}
            </div>
          </div>

          <div className="info-section">
            <h3>Operating Countries</h3>
            <div className="countries-list">
              {Array.isArray(data['List of countries they operate in'])
                ? data['List of countries they operate in'].join(', ')
                : data['List of countries they operate in']}
            </div>
          </div>

          <div className="info-section">
            <h3>About</h3>
            <p>{data['brief about company']}</p>
          </div>

          <div className="info-section">
            <h3>Compliance Requirements</h3>
            <div className="compliance-tags">
              {Array.isArray(data['Compliance Requirements'])
                ? data['Compliance Requirements'].map((req, idx) => (
                    <span key={idx} className="compliance-tag">{req}</span>
                  ))
                : <span className="compliance-tag">{data['Compliance Requirements']}</span>}
            </div>
          </div>

          {/* Inline Configuration Form */}
          {results.show_form && results.presumptive_config && (
            <InlineConfigForm
              messageId={messageId}
              initialData={results.presumptive_config}
              onSubmit={(formData) => handleConfigSubmit(messageId, formData)}
              saveStatus={formSaveStatus[messageId]}
            />
          )}
        </div>
      );
    }

    if (results.mode === 'company_list') {
      // Mode 1: Company list with numbers
      const companies = results.companies;

      if (!companies || companies.length === 0) {
        return <p>{results.message || 'No companies found.'}</p>;
      }

      return (
        <div>
          <p style={{ marginBottom: '12px', fontWeight: 'bold' }}>
            {results.message || `Found ${results.count} companies:`}
          </p>
          {companies.map((company) => (
            <div key={company.number} className="company-card">
              <div className="company-number">{company.number}</div>
              <div className="company-details">
                <h3>{company.name || 'N/A'}</h3>
                {company.description && <p>{company.description}</p>}
                {company.industry && (
                  <p>
                    <strong>Industry:</strong> {company.industry}
                  </p>
                )}
                {company.location && (
                  <p>
                    <strong>Location:</strong> {company.location}
                  </p>
                )}
                {company.website && (
                  <p>
                    <strong>Website:</strong>{' '}
                    <a href={company.website} target="_blank" rel="noopener noreferrer">
                      {company.website}
                    </a>
                  </p>
                )}
              </div>
            </div>
          ))}
          <p style={{ marginTop: '16px', fontStyle: 'italic', color: '#666' }}>
            💡 Enter a number (1-{companies.length}) to get detailed information
          </p>
        </div>
      );
    }

    // Fallback for old format or errors
    if (!results.success) {
      return (
        <div className="error-message">
          Error: {results.error || 'Failed to fetch company information'}
        </div>
      );
    }

    return <p>No data available</p>;
  };

  // Inline Configuration Form Component (for chat messages)
  const InlineConfigForm = ({ messageId, initialData, onSubmit, saveStatus }) => {
    const [formData, setFormData] = useState(initialData || {});

    const industrySectors = [
      'Aerospace & Defense',
      'Agriculture & Farming',
      'Automotive',
      'Banking & Financial Services',
      'Biotechnology',
      'Chemicals',
      'Construction & Real Estate',
      'Consumer Goods & Retail',
      'Education',
      'Energy & Utilities',
      'Entertainment & Media',
      'Food & Beverage',
      'Government & Public Sector',
      'Healthcare & Pharmaceuticals',
      'Hospitality & Tourism',
      'Insurance',
      'Legal Services',
      'Logistics & Transportation',
      'Manufacturing',
      'Mining & Metals',
      'Non-Profit & NGO',
      'Oil & Gas',
      'Professional Services',
      'Telecommunications',
      'Technology & Software',
      'Textiles & Apparel',
      'Others'
    ];

    const subSectorOptions = {
      'Aerospace & Defense': [
        'Aircraft Manufacturing',
        'Defense Contractors',
        'Space Technology',
        'Aviation Services',
        'Defense Electronics',
        'Military Equipment',
        'Satellite Systems',
        'Drones & UAV'
      ],
      'Agriculture & Farming': [
        'Crop Production',
        'Livestock & Dairy',
        'Agricultural Equipment',
        'AgriTech',
        'Organic Farming',
        'Aquaculture',
        'Forestry',
        'Seeds & Fertilizers'
      ],
      'Automotive': [
        'Automobile Manufacturing',
        'Auto Parts & Components',
        'Electric Vehicles (EV)',
        'Autonomous Vehicles',
        'Two-Wheelers',
        'Commercial Vehicles',
        'Auto Dealerships',
        'Aftermarket Services'
      ],
      'Banking & Financial Services': [
        'Retail Banking',
        'Commercial Banking',
        'Investment Banking',
        'FinTech',
        'Wealth Management',
        'Asset Management',
        'Payment Processing',
        'Digital Banking',
        'Microfinance',
        'Credit Unions'
      ],
      'Biotechnology': [
        'Biopharmaceuticals',
        'Genetic Engineering',
        'Agricultural Biotech',
        'Industrial Biotechnology',
        'Bioinformatics',
        'Gene Therapy',
        'Synthetic Biology',
        'Biomedical Engineering'
      ],
      'Chemicals': [
        'Specialty Chemicals',
        'Petrochemicals',
        'Agricultural Chemicals',
        'Industrial Chemicals',
        'Polymers & Plastics',
        'Pharmaceuticals Chemicals',
        'Fine Chemicals',
        'Paint & Coatings'
      ],
      'Construction & Real Estate': [
        'Residential Construction',
        'Commercial Construction',
        'Infrastructure Development',
        'Real Estate Development',
        'Property Management',
        'REITs',
        'Construction Materials',
        'Architecture & Design',
        'PropTech'
      ],
      'Consumer Goods & Retail': [
        'E-commerce',
        'Department Stores',
        'Specialty Retail',
        'Fast Fashion',
        'Luxury Goods',
        'Consumer Electronics',
        'Home Furnishings',
        'Supermarkets & Grocery',
        'Direct-to-Consumer (D2C)',
        'FMCG'
      ],
      'Education': [
        'K-12 Education',
        'Higher Education',
        'EdTech',
        'Online Learning Platforms',
        'Vocational Training',
        'Test Preparation',
        'Corporate Training',
        'Educational Content',
        'Student Services',
        'International Education'
      ],
      'Energy & Utilities': [
        'Electric Utilities',
        'Water & Waste Management',
        'Renewable Energy',
        'Solar Power',
        'Wind Energy',
        'Hydroelectric Power',
        'Nuclear Energy',
        'Energy Storage',
        'Smart Grid',
        'Gas Distribution'
      ],
      'Entertainment & Media': [
        'Film Production',
        'Broadcasting',
        'Streaming Services',
        'Music Industry',
        'Publishing',
        'Gaming',
        'Sports & Entertainment',
        'Advertising',
        'Digital Media',
        'Social Media'
      ],
      'Food & Beverage': [
        'Food Processing',
        'Beverage Manufacturing',
        'Restaurants & QSR',
        'Food Delivery',
        'Packaged Foods',
        'Dairy Products',
        'Bakery & Confectionery',
        'Alcoholic Beverages',
        'Non-Alcoholic Beverages',
        'Food Tech'
      ],
      'Government & Public Sector': [
        'Federal Government',
        'State/Provincial Government',
        'Municipal Government',
        'Defense & Military',
        'Public Safety',
        'Regulatory Agencies',
        'Public Transportation',
        'Government IT',
        'Civic Services'
      ],
      'Healthcare & Pharmaceuticals': [
        'Hospitals & Clinics',
        'Pharmaceutical Manufacturing',
        'Medical Devices',
        'Telemedicine',
        'Health Insurance',
        'Clinical Research',
        'Diagnostics',
        'Home Healthcare',
        'Mental Health Services',
        'Healthcare IT',
        'Medical Equipment',
        'Drug Discovery'
      ],
      'Hospitality & Tourism': [
        'Hotels & Resorts',
        'Travel Agencies',
        'Airlines',
        'Cruise Lines',
        'Event Management',
        'Theme Parks',
        'Online Travel Booking',
        'Vacation Rentals',
        'Tourism Boards',
        'Restaurant Chains'
      ],
      'Insurance': [
        'Life Insurance',
        'Health Insurance',
        'Property & Casualty',
        'Auto Insurance',
        'InsurTech',
        'Reinsurance',
        'Commercial Insurance',
        'Specialty Insurance',
        'Insurance Brokers'
      ],
      'Legal Services': [
        'Corporate Law',
        'Litigation',
        'Intellectual Property',
        'Legal Technology',
        'Legal Process Outsourcing',
        'Compliance & Regulatory',
        'Immigration Law',
        'Tax Law',
        'Real Estate Law'
      ],
      'Logistics & Transportation': [
        'Freight & Shipping',
        'Warehousing',
        'Last-Mile Delivery',
        'Supply Chain Management',
        'Third-Party Logistics (3PL)',
        'Fleet Management',
        'Rail Transport',
        'Maritime Shipping',
        'Air Cargo',
        'Logistics Technology'
      ],
      'Manufacturing': [
        'Industrial Manufacturing',
        'Consumer Goods Manufacturing',
        'Electronics Manufacturing',
        'Textile Manufacturing',
        'Metal Fabrication',
        'Machinery & Equipment',
        'Semiconductor Manufacturing',
        'Contract Manufacturing',
        'Additive Manufacturing (3D Printing)',
        'Process Manufacturing'
      ],
      'Mining & Metals': [
        'Coal Mining',
        'Metal Ore Mining',
        'Gold & Precious Metals',
        'Industrial Minerals',
        'Steel Production',
        'Aluminum Production',
        'Copper Mining',
        'Rare Earth Elements',
        'Mining Equipment',
        'Mineral Processing'
      ],
      'Non-Profit & NGO': [
        'Charitable Organizations',
        'International Development',
        'Environmental Conservation',
        'Human Rights',
        'Education Foundations',
        'Healthcare Charities',
        'Disaster Relief',
        'Social Services',
        'Advocacy Groups',
        'Research Foundations'
      ],
      'Oil & Gas': [
        'Upstream (Exploration & Production)',
        'Midstream (Transportation & Storage)',
        'Downstream (Refining & Distribution)',
        'Oilfield Services',
        'Petrochemicals',
        'LNG',
        'Offshore Drilling',
        'Pipeline Operations',
        'Energy Trading'
      ],
      'Professional Services': [
        'Consulting',
        'Accounting & Audit',
        'Management Consulting',
        'HR Consulting',
        'Market Research',
        'Public Relations',
        'Business Process Outsourcing',
        'IT Consulting',
        'Strategy Consulting',
        'Tax Advisory'
      ],
      'Telecommunications': [
        'Mobile Network Operators',
        'Fixed-Line Telecom',
        'Internet Service Providers (ISP)',
        'Satellite Communications',
        'Telecom Equipment',
        '5G Infrastructure',
        'Network Security',
        'Unified Communications',
        'VoIP Services',
        'Telecom Software'
      ],
      'Technology & Software': [
        'Software as a Service (SaaS)',
        'Cloud Services',
        'Cybersecurity',
        'Artificial Intelligence & ML',
        'Enterprise Software',
        'Mobile Applications',
        'DevOps & Infrastructure',
        'Data Analytics',
        'Blockchain',
        'IoT (Internet of Things)',
        'E-commerce Platforms',
        'CRM Software',
        'ERP Systems',
        'Business Intelligence',
        'Software Development'
      ],
      'Textiles & Apparel': [
        'Textile Manufacturing',
        'Garment Manufacturing',
        'Fashion Design',
        'Footwear',
        'Sportswear',
        'Luxury Fashion',
        'Fast Fashion',
        'Technical Textiles',
        'Home Textiles',
        'Apparel Retail'
      ],
      'Others': [
        'Environmental Services',
        'Security Services',
        'Facility Management',
        'Printing & Packaging',
        'Waste Management',
        'Research & Development',
        'Think Tanks',
        'Trade Associations',
        'Membership Organizations',
        'Other Industries'
      ]
    };

    const cloudProviders = ['AWS', 'Azure', 'GCP'];
    const continents = ['North America', 'Europe', 'Asia Pacific', 'Middle East', 'South America'];
    const regionStrategies = ['Single Region', 'Dual Primary Regions', 'Primary + DR'];

    const handleChange = (field, value) => {
      const newData = { ...formData, [field]: value };

      // Reset sub-sector if industry sector changes
      if (field === 'industry_sector') {
        newData.sub_sector = subSectorOptions[value]?.[0] || '';
      }

      setFormData(newData);
    };

    const handleFormSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <div className="inline-config-form-section">
        <h3 className="form-section-title">Presumptive Configuration</h3>
        <p className="form-section-description">
          Based on the company information, we've pre-selected these values.
          Please review and modify as needed.
        </p>

        <form onSubmit={handleFormSubmit} className="inline-config-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor={`industry_sector_${messageId}`}>Industry Sector *</label>
              <select
                id={`industry_sector_${messageId}`}
                value={formData.industry_sector || ''}
                onChange={(e) => handleChange('industry_sector', e.target.value)}
                required
                disabled={saveStatus === 'saving'}
              >
                {industrySectors.map(sector => (
                  <option key={sector} value={sector}>{sector}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor={`sub_sector_${messageId}`}>Sub-Sector *</label>
              <select
                id={`sub_sector_${messageId}`}
                value={formData.sub_sector || ''}
                onChange={(e) => handleChange('sub_sector', e.target.value)}
                required
                disabled={saveStatus === 'saving'}
              >
                {(subSectorOptions[formData.industry_sector] || []).map(subSector => (
                  <option key={subSector} value={subSector}>{subSector}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor={`cloud_provider_${messageId}`}>Cloud Provider *</label>
              <select
                id={`cloud_provider_${messageId}`}
                value={formData.cloud_provider || ''}
                onChange={(e) => handleChange('cloud_provider', e.target.value)}
                required
                disabled={saveStatus === 'saving'}
              >
                {cloudProviders.map(provider => (
                  <option key={provider} value={provider}>{provider}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor={`target_continent_${messageId}`}>Target Continent *</label>
              <select
                id={`target_continent_${messageId}`}
                value={formData.target_continent || ''}
                onChange={(e) => handleChange('target_continent', e.target.value)}
                required
                disabled={saveStatus === 'saving'}
              >
                {continents.map(continent => (
                  <option key={continent} value={continent}>{continent}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group form-group-full">
              <label htmlFor={`region_strategy_${messageId}`}>Region Deployment Strategy *</label>
              <select
                id={`region_strategy_${messageId}`}
                value={formData.region_strategy || ''}
                onChange={(e) => handleChange('region_strategy', e.target.value)}
                required
                disabled={saveStatus === 'saving'}
              >
                {regionStrategies.map(strategy => (
                  <option key={strategy} value={strategy}>{strategy}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-footer">
            {saveStatus && (
              <div className={`save-status save-status-${saveStatus}`}>
                {saveStatus === 'saving' && '⏳ Saving configuration...'}
                {saveStatus === 'saved' && '✓ Configuration saved successfully!'}
                {saveStatus === 'error' && '✗ Failed to save. Please try again.'}
              </div>
            )}
            <button
              type="submit"
              className="continue-btn-inline"
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Saving...' : 'Continue Questionnaire'}
            </button>
          </div>
        </form>
      </div>
    );
  };

  // Configuration Form Component (OLD - KEEP FOR NOW, WILL REMOVE)
  const ConfigurationForm = ({ initialData, onSubmit, loading }) => {
    const [formData, setFormData] = useState(initialData || {});

    const industrySectors = [
      'Aerospace & Defense',
      'Agriculture & Farming',
      'Automotive',
      'Banking & Financial Services',
      'Biotechnology',
      'Chemicals',
      'Construction & Real Estate',
      'Consumer Goods & Retail',
      'Education',
      'Energy & Utilities',
      'Entertainment & Media',
      'Food & Beverage',
      'Government & Public Sector',
      'Healthcare & Pharmaceuticals',
      'Hospitality & Tourism',
      'Insurance',
      'Legal Services',
      'Logistics & Transportation',
      'Manufacturing',
      'Mining & Metals',
      'Non-Profit & NGO',
      'Oil & Gas',
      'Professional Services',
      'Telecommunications',
      'Technology & Software',
      'Textiles & Apparel',
      'Others'
    ];

    const subSectorOptions = {
      'Aerospace & Defense': [
        'Aircraft Manufacturing',
        'Defense Contractors',
        'Space Technology',
        'Aviation Services',
        'Defense Electronics',
        'Military Equipment',
        'Satellite Systems',
        'Drones & UAV'
      ],
      'Agriculture & Farming': [
        'Crop Production',
        'Livestock & Dairy',
        'Agricultural Equipment',
        'AgriTech',
        'Organic Farming',
        'Aquaculture',
        'Forestry',
        'Seeds & Fertilizers'
      ],
      'Automotive': [
        'Automobile Manufacturing',
        'Auto Parts & Components',
        'Electric Vehicles (EV)',
        'Autonomous Vehicles',
        'Two-Wheelers',
        'Commercial Vehicles',
        'Auto Dealerships',
        'Aftermarket Services'
      ],
      'Banking & Financial Services': [
        'Retail Banking',
        'Commercial Banking',
        'Investment Banking',
        'FinTech',
        'Wealth Management',
        'Asset Management',
        'Payment Processing',
        'Digital Banking',
        'Microfinance',
        'Credit Unions'
      ],
      'Biotechnology': [
        'Biopharmaceuticals',
        'Genetic Engineering',
        'Agricultural Biotech',
        'Industrial Biotechnology',
        'Bioinformatics',
        'Gene Therapy',
        'Synthetic Biology',
        'Biomedical Engineering'
      ],
      'Chemicals': [
        'Specialty Chemicals',
        'Petrochemicals',
        'Agricultural Chemicals',
        'Industrial Chemicals',
        'Polymers & Plastics',
        'Pharmaceuticals Chemicals',
        'Fine Chemicals',
        'Paint & Coatings'
      ],
      'Construction & Real Estate': [
        'Residential Construction',
        'Commercial Construction',
        'Infrastructure Development',
        'Real Estate Development',
        'Property Management',
        'REITs',
        'Construction Materials',
        'Architecture & Design',
        'PropTech'
      ],
      'Consumer Goods & Retail': [
        'E-commerce',
        'Department Stores',
        'Specialty Retail',
        'Fast Fashion',
        'Luxury Goods',
        'Consumer Electronics',
        'Home Furnishings',
        'Supermarkets & Grocery',
        'Direct-to-Consumer (D2C)',
        'FMCG'
      ],
      'Education': [
        'K-12 Education',
        'Higher Education',
        'EdTech',
        'Online Learning Platforms',
        'Vocational Training',
        'Test Preparation',
        'Corporate Training',
        'Educational Content',
        'Student Services',
        'International Education'
      ],
      'Energy & Utilities': [
        'Electric Utilities',
        'Water & Waste Management',
        'Renewable Energy',
        'Solar Power',
        'Wind Energy',
        'Hydroelectric Power',
        'Nuclear Energy',
        'Energy Storage',
        'Smart Grid',
        'Gas Distribution'
      ],
      'Entertainment & Media': [
        'Film Production',
        'Broadcasting',
        'Streaming Services',
        'Music Industry',
        'Publishing',
        'Gaming',
        'Sports & Entertainment',
        'Advertising',
        'Digital Media',
        'Social Media'
      ],
      'Food & Beverage': [
        'Food Processing',
        'Beverage Manufacturing',
        'Restaurants & QSR',
        'Food Delivery',
        'Packaged Foods',
        'Dairy Products',
        'Bakery & Confectionery',
        'Alcoholic Beverages',
        'Non-Alcoholic Beverages',
        'Food Tech'
      ],
      'Government & Public Sector': [
        'Federal Government',
        'State/Provincial Government',
        'Municipal Government',
        'Defense & Military',
        'Public Safety',
        'Regulatory Agencies',
        'Public Transportation',
        'Government IT',
        'Civic Services'
      ],
      'Healthcare & Pharmaceuticals': [
        'Hospitals & Clinics',
        'Pharmaceutical Manufacturing',
        'Medical Devices',
        'Telemedicine',
        'Health Insurance',
        'Clinical Research',
        'Diagnostics',
        'Home Healthcare',
        'Mental Health Services',
        'Healthcare IT',
        'Medical Equipment',
        'Drug Discovery'
      ],
      'Hospitality & Tourism': [
        'Hotels & Resorts',
        'Travel Agencies',
        'Airlines',
        'Cruise Lines',
        'Event Management',
        'Theme Parks',
        'Online Travel Booking',
        'Vacation Rentals',
        'Tourism Boards',
        'Restaurant Chains'
      ],
      'Insurance': [
        'Life Insurance',
        'Health Insurance',
        'Property & Casualty',
        'Auto Insurance',
        'InsurTech',
        'Reinsurance',
        'Commercial Insurance',
        'Specialty Insurance',
        'Insurance Brokers'
      ],
      'Legal Services': [
        'Corporate Law',
        'Litigation',
        'Intellectual Property',
        'Legal Technology',
        'Legal Process Outsourcing',
        'Compliance & Regulatory',
        'Immigration Law',
        'Tax Law',
        'Real Estate Law'
      ],
      'Logistics & Transportation': [
        'Freight & Shipping',
        'Warehousing',
        'Last-Mile Delivery',
        'Supply Chain Management',
        'Third-Party Logistics (3PL)',
        'Fleet Management',
        'Rail Transport',
        'Maritime Shipping',
        'Air Cargo',
        'Logistics Technology'
      ],
      'Manufacturing': [
        'Industrial Manufacturing',
        'Consumer Goods Manufacturing',
        'Electronics Manufacturing',
        'Textile Manufacturing',
        'Metal Fabrication',
        'Machinery & Equipment',
        'Semiconductor Manufacturing',
        'Contract Manufacturing',
        'Additive Manufacturing (3D Printing)',
        'Process Manufacturing'
      ],
      'Mining & Metals': [
        'Coal Mining',
        'Metal Ore Mining',
        'Gold & Precious Metals',
        'Industrial Minerals',
        'Steel Production',
        'Aluminum Production',
        'Copper Mining',
        'Rare Earth Elements',
        'Mining Equipment',
        'Mineral Processing'
      ],
      'Non-Profit & NGO': [
        'Charitable Organizations',
        'International Development',
        'Environmental Conservation',
        'Human Rights',
        'Education Foundations',
        'Healthcare Charities',
        'Disaster Relief',
        'Social Services',
        'Advocacy Groups',
        'Research Foundations'
      ],
      'Oil & Gas': [
        'Upstream (Exploration & Production)',
        'Midstream (Transportation & Storage)',
        'Downstream (Refining & Distribution)',
        'Oilfield Services',
        'Petrochemicals',
        'LNG',
        'Offshore Drilling',
        'Pipeline Operations',
        'Energy Trading'
      ],
      'Professional Services': [
        'Consulting',
        'Accounting & Audit',
        'Management Consulting',
        'HR Consulting',
        'Market Research',
        'Public Relations',
        'Business Process Outsourcing',
        'IT Consulting',
        'Strategy Consulting',
        'Tax Advisory'
      ],
      'Telecommunications': [
        'Mobile Network Operators',
        'Fixed-Line Telecom',
        'Internet Service Providers (ISP)',
        'Satellite Communications',
        'Telecom Equipment',
        '5G Infrastructure',
        'Network Security',
        'Unified Communications',
        'VoIP Services',
        'Telecom Software'
      ],
      'Technology & Software': [
        'Software as a Service (SaaS)',
        'Cloud Services',
        'Cybersecurity',
        'Artificial Intelligence & ML',
        'Enterprise Software',
        'Mobile Applications',
        'DevOps & Infrastructure',
        'Data Analytics',
        'Blockchain',
        'IoT (Internet of Things)',
        'E-commerce Platforms',
        'CRM Software',
        'ERP Systems',
        'Business Intelligence',
        'Software Development'
      ],
      'Textiles & Apparel': [
        'Textile Manufacturing',
        'Garment Manufacturing',
        'Fashion Design',
        'Footwear',
        'Sportswear',
        'Luxury Fashion',
        'Fast Fashion',
        'Technical Textiles',
        'Home Textiles',
        'Apparel Retail'
      ],
      'Others': [
        'Environmental Services',
        'Security Services',
        'Facility Management',
        'Printing & Packaging',
        'Waste Management',
        'Research & Development',
        'Think Tanks',
        'Trade Associations',
        'Membership Organizations',
        'Other Industries'
      ]
    };

    const cloudProviders = ['AWS', 'Azure', 'GCP'];
    const continents = ['North America', 'Europe', 'Asia Pacific', 'Middle East', 'South America'];
    const regionStrategies = ['Single Region', 'Dual Primary Regions', 'Primary + DR'];

    const handleChange = (field, value) => {
      const newData = { ...formData, [field]: value };

      // Reset sub-sector if industry sector changes
      if (field === 'industry_sector') {
        newData.sub_sector = subSectorOptions[value]?.[0] || '';
      }

      setFormData(newData);
    };

    const handleFormSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <div className="config-form-container">
        <div className="config-form-overlay" />
        <div className="config-form">
          <h2>Presumptive Configuration</h2>
          <p className="form-description">
            Based on the company information, we've pre-selected these values.
            Please review and modify as needed.
          </p>

          <form onSubmit={handleFormSubmit}>
            <div className="form-group">
              <label htmlFor="industry_sector">Industry Sector *</label>
              <select
                id="industry_sector"
                value={formData.industry_sector || ''}
                onChange={(e) => handleChange('industry_sector', e.target.value)}
                required
                disabled={loading}
              >
                {industrySectors.map(sector => (
                  <option key={sector} value={sector}>{sector}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="sub_sector">Sub-Sector *</label>
              <select
                id="sub_sector"
                value={formData.sub_sector || ''}
                onChange={(e) => handleChange('sub_sector', e.target.value)}
                required
                disabled={loading}
              >
                {(subSectorOptions[formData.industry_sector] || []).map(subSector => (
                  <option key={subSector} value={subSector}>{subSector}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="cloud_provider">Cloud Provider *</label>
              <select
                id="cloud_provider"
                value={formData.cloud_provider || ''}
                onChange={(e) => handleChange('cloud_provider', e.target.value)}
                required
                disabled={loading}
              >
                {cloudProviders.map(provider => (
                  <option key={provider} value={provider}>{provider}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="target_continent">Target Continent *</label>
              <select
                id="target_continent"
                value={formData.target_continent || ''}
                onChange={(e) => handleChange('target_continent', e.target.value)}
                required
                disabled={loading}
              >
                {continents.map(continent => (
                  <option key={continent} value={continent}>{continent}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="region_strategy">Region Deployment Strategy *</label>
              <select
                id="region_strategy"
                value={formData.region_strategy || ''}
                onChange={(e) => handleChange('region_strategy', e.target.value)}
                required
                disabled={loading}
              >
                {regionStrategies.map(strategy => (
                  <option key={strategy} value={strategy}>{strategy}</option>
                ))}
              </select>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="continue-btn"
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Continue Questionnaire'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={createNewChat}>
            <FiPlus /> New Chat
          </button>
        </div>
        <div className="chat-history">
          {sessionsLoading ? (
            <div className="loading-sessions">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="no-sessions">No sessions yet</div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`chat-history-item ${currentSessionId === session.id ? 'active' : ''}`}
              >
                <button
                  className="session-button"
                  onClick={() => selectSession(session.id)}
                >
                  <FiMessageSquare />
                  <span className="session-title">{session.title}</span>
                </button>
                <button
                  className="delete-session-btn"
                  onClick={(e) => deleteSession(session.id, e)}
                  title="Delete session"
                >
                  <FiTrash2 />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1>Company Search Agent</h1>
              <p>Search for companies by name to get a numbered list.</p>
              <p>Then enter a number to get detailed company information.</p>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div className="message-icon">
                    {message.role === 'user' ? <FiUser /> : <BsRobot />}
                  </div>
                  <div className="message-content">
                    {message.role === 'user' ? (
                      <p>{message.content}</p>
                    ) : (
                      renderCompanyResults(message.content, message.id)
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="message assistant">
                  <div className="message-icon">
                    <BsRobot />
                  </div>
                  <div className="message-content">
                    <div className="loading">
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Input Container */}
        <div className="input-container">
          <div className="input-wrapper">
            <form className="input-form" onSubmit={handleSubmit}>
              <input
                type="text"
                className="input-field"
                placeholder="Enter company name or number... (e.g., metlife or 1)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={loading || !input.trim()}
              >
                <FiSend />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
