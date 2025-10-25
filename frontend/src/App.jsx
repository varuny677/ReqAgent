import { useState, useEffect, useRef } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { FiPlus, FiSend, FiMessageSquare, FiUser, FiTrash2, FiMenu, FiX, FiSun, FiMoon } from 'react-icons/fi';
import { BsRobot } from 'react-icons/bs';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';
import Questionnaire from './pages/Questionnaire';

const API_BASE_URL = 'http://localhost:8000';

function ChatInterface({ currentSessionId, setCurrentSessionId, onSessionsChange, theme, toggleTheme }) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [companyList, setCompanyList] = useState(null); // Store company list internally
  const [hasDetailedView, setHasDetailedView] = useState(false); // Track if showing detailed view

  // Form state
  const [formSaveStatus, setFormSaveStatus] = useState({}); // Track save status per message

  const messagesEndRef = useRef(null);
  const searchInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load session when currentSessionId changes
  useEffect(() => {
    if (currentSessionId) {
      loadSession(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  const loadSession = async (sessionId) => {
    try {
      setLoading(true);
      setError(null);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput('');
    setError(null);
    setSearchExpanded(true); // Keep search bar expanded during fetch

    // DON'T add user message to UI - keep search silent
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

      const results = response.data.results;

      // If it's a company list, store it internally and show cards
      if (results.mode === 'company_list' && results.companies) {
        setCompanyList(results.companies);
        setHasDetailedView(false);

        // Add only the assistant response (company cards)
        const assistantMessage = {
          id: response.data.message_id,
          role: 'assistant',
          content: results,
          timestamp: new Date().toISOString(),
        };
        setMessages([assistantMessage]); // Replace messages with just the results
      } else {
        // For other responses, add to messages
        const assistantMessage = {
          id: response.data.message_id,
          role: 'assistant',
          content: results,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }

      // Refresh sessions list to show the new/updated session
      await onSessionsChange();

    } catch (err) {
      console.error('Error searching companies:', err);
      setError(
        err.response?.data?.detail ||
        'Failed to search companies. Please make sure the backend server and Temporal worker are running.'
      );
    } finally {
      setLoading(false);
      // Re-enable search bar after results appear
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
      // Mode 1: Company list as cards
      const companies = results.companies;

      if (!companies || companies.length === 0) {
        return <p>{results.message || 'No companies found.'}</p>;
      }

      const handleSelectCompany = async (companyNumber) => {
        // Directly fetch company details without showing number in UI
        setLoading(true);
        setError(null);
        setHasDetailedView(true); // Mark that we're showing details

        try {
          const response = await axios.post(`${API_BASE_URL}/api/search`, {
            query: companyNumber.toString(),
            session_id: currentSessionId,
          });

          // Replace messages with detailed view (no number shown)
          const assistantMessage = {
            id: response.data.message_id,
            role: 'assistant',
            content: response.data.results,
            timestamp: new Date().toISOString(),
          };
          setMessages([assistantMessage]); // Replace with just the detailed info
          await onSessionsChange();
        } catch (err) {
          console.error('Error selecting company:', err);
          setError('Failed to load company details');
        } finally {
          setLoading(false);
        }
      };

      return (
        <div className="company-cards-container">
          <div className="company-cards-grid">
            {companies.map((company) => (
              <motion.div
                key={company.number}
                className="company-card-modern"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: company.number * 0.1 }}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
              >
                <div className="company-card-header">
                  <h3>{company.name || 'N/A'}</h3>
                  {company.industry && (
                    <span className="company-industry-tag">{company.industry}</span>
                  )}
                </div>
                <div className="company-card-body">
                  {company.description && <p className="company-description">{company.description}</p>}
                  {company.location && (
                    <p className="company-info-item">
                      <strong>Location:</strong> {company.location}
                    </p>
                  )}
                  {company.website && (
                    <p className="company-info-item company-website">
                      <strong>Website:</strong>{' '}
                      <a href={company.website} target="_blank" rel="noopener noreferrer">
                        {company.website}
                      </a>
                    </p>
                  )}
                </div>
                <button
                  className="company-select-btn"
                  onClick={() => handleSelectCompany(company.number)}
                >
                  Select
                </button>
              </motion.div>
            ))}
          </div>
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

    const handleContinueQuestionnaire = (e) => {
      e.preventDefault();
      // Save the form first, then navigate
      onSubmit(formData);
      // Navigate to questionnaire after a brief delay to allow save to complete
      setTimeout(() => {
        navigate(`/questionnaire/${currentSessionId}`);
      }, 500);
    };

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

    const cloudProviders = ['AWS', 'Azure'];
    const continents = ['North America', 'Europe', 'Asia Pacific', 'Middle East', 'South America'];
    const regionStrategies = ['Single Region', 'Primary + DR'];

    const handleChange = (field, value) => {
      const newData = { ...formData, [field]: value };

      // Reset sub-sector if industry sector changes
      if (field === 'industry_sector') {
        newData.sub_sector = subSectorOptions[value]?.[0] || '';
      }

      setFormData(newData);
    };

    return (
      <div className="inline-config-form-section">
        <h3 className="form-section-title">Presumptive Configuration</h3>
        <p className="form-section-description">
          Based on the company information, we've pre-selected these values.
          Please review and modify as needed.
        </p>

        <form onSubmit={handleContinueQuestionnaire} className="inline-config-form">
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

    const cloudProviders = ['AWS', 'Azure'];
    const continents = ['North America', 'Europe', 'Asia Pacific', 'Middle East', 'South America'];
    const regionStrategies = ['Single Region', 'Primary + DR'];

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
    <div className="main-content">
        {/* Theme Toggle Button */}
        <button className="theme-toggle-btn" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? <FiSun /> : <FiMoon />}
        </button>

        {/* Search Bar - Always visible at top, disabled when viewing details */}
        <motion.div
          className={`search-bar-container-top ${searchExpanded ? 'expanded' : ''}`}
          initial={false}
          animate={{
            width: searchExpanded ? '90%' : '500px',
          }}
          transition={{ duration: 0.35, ease: [0.4, 0.0, 0.2, 1] }}
        >
          <form className={`search-bar-form ${loading || hasDetailedView ? 'disabled' : ''}`} onSubmit={handleSubmit}>
            <input
              ref={searchInputRef}
              type="text"
              className="search-bar-input"
              placeholder={loading ? "Searching..." : "Search for companies..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => !loading && !hasDetailedView && setSearchExpanded(true)}
              onBlur={() => !loading && !hasDetailedView && setSearchExpanded(false)}
              disabled={loading || hasDetailedView}
            />
            <button
              type="submit"
              className="search-submit-btn"
              disabled={loading || !input.trim() || hasDetailedView}
            >
              ▶
            </button>
          </form>

          {/* Spinner below search bar when loading */}
          {loading && (
            <div className="search-loading-spinner">
              <div className="spinner"></div>
            </div>
          )}
        </motion.div>

        {/* Main Content Area */}
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1>Company Search Agent</h1>
              <p>Search for companies by name to get top 3 matches.</p>
              <p>Click on a company card to get detailed information.</p>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  {message.role === 'assistant' && (
                    <div className="message-content-full">
                      {renderCompanyResults(message.content, message.id)}
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="loading-overlay">
                  <div className="loading">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
  );
}

// Sidebar component that persists across routes
function Sidebar({ sessions, currentSessionId, sessionsLoading, onNewChat, onSelectSession, onDeleteSession }) {
  // State for sidebar collapse - persisted in localStorage
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved ? JSON.parse(saved) : false;
  });

  // Save collapse state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(isCollapsed));
  }, [isCollapsed]);

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  // Framer Motion variants for smooth animation
  const sidebarVariants = {
    expanded: {
      width: 260,
      transition: {
        duration: 0.35,
        ease: [0.4, 0.0, 0.2, 1] // Custom easing for smooth feel
      }
    },
    collapsed: {
      width: 0,
      transition: {
        duration: 0.35,
        ease: [0.4, 0.0, 0.2, 1]
      }
    }
  };

  const contentVariants = {
    expanded: {
      opacity: 1,
      transition: {
        duration: 0.25,
        delay: 0.1
      }
    },
    collapsed: {
      opacity: 0,
      transition: {
        duration: 0.15
      }
    }
  };

  return (
    <>
      {/* Toggle Button - Always visible */}
      <button
        className={`sidebar-toggle-btn ${isCollapsed ? 'collapsed' : ''}`}
        onClick={toggleSidebar}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <FiMenu size={20} /> : <FiX size={20} />}
      </button>

      {/* Animated Sidebar */}
      <motion.div
        className="sidebar"
        initial={false}
        animate={isCollapsed ? "collapsed" : "expanded"}
        variants={sidebarVariants}
      >
        <motion.div
          className="sidebar-content"
          variants={contentVariants}
          animate={isCollapsed ? "collapsed" : "expanded"}
        >
          <div className="sidebar-header">
            <button className="new-chat-btn" onClick={onNewChat}>
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
                    onClick={() => onSelectSession(session.id)}
                  >
                    <FiMessageSquare />
                    <span className="session-title">{session.title}</span>
                  </button>
                  <button
                    className="delete-session-btn"
                    onClick={(e) => onDeleteSession(session.id, e)}
                    title="Delete session"
                  >
                    <FiTrash2 />
                  </button>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </motion.div>
    </>
  );
}

// Main App component with routing
function App() {
  // We'll manage sessions at the App level so they persist across routes
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const navigate = useNavigate();

  // Theme management with localStorage persistence
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved || 'dark';
  });

  useEffect(() => {
    fetchSessions();
  }, []);

  // Apply theme to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

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

  const createNewChat = () => {
    setCurrentSessionId(null);
    navigate('/');
  };

  const selectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    navigate('/');
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this session?')) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/sessions/${sessionId}`);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
    } catch (err) {
      console.error('Error deleting session:', err);
    }
  };

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        sessionsLoading={sessionsLoading}
        onNewChat={createNewChat}
        onSelectSession={selectSession}
        onDeleteSession={deleteSession}
      />
      <Routes>
        <Route
          path="/"
          element={
            <ChatInterface
              currentSessionId={currentSessionId}
              setCurrentSessionId={setCurrentSessionId}
              onSessionsChange={fetchSessions}
              theme={theme}
              toggleTheme={toggleTheme}
            />
          }
        />
        <Route path="/questionnaire/:sessionId" element={<Questionnaire />} />
      </Routes>
    </div>
  );
}

export default App;
