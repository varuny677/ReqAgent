import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import awsQuestionsData from '../../../qna/Questions.json';
import azureQuestionsData from '../../../qna/questionsazure.json';
import './Questionnaire.css';

const API_BASE_URL = 'http://localhost:8000';

function Questionnaire() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  // State
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [aiPredictions, setAiPredictions] = useState({});
  const [aiAssumptions, setAiAssumptions] = useState({});
  const [expandedAssumptions, setExpandedAssumptions] = useState({});
  const [visibleQuestions, setVisibleQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [companyData, setCompanyData] = useState(null);
  const [configData, setConfigData] = useState(null);
  const [error, setError] = useState(null);

  // Load company info and configuration on mount
  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  // Load appropriate questions based on cloud provider
  useEffect(() => {
    if (configData?.cloud_provider) {
      loadQuestionsByProvider(configData.cloud_provider);
    }
  }, [configData]);

  // Compute visible questions whenever answers change
  useEffect(() => {
    if (questions.length > 0) {
      computeVisibleQuestions();
    }
  }, [answers, questions]);

  // Auto-trigger AI analysis when visible questions change
  useEffect(() => {
    if (visibleQuestions.length > 0 && companyData && configData) {
      const unansweredQuestions = visibleQuestions.filter(
        (qId) => !answers[qId] && questions.find(q => q.id === qId)?.type !== 'section'
      );

      if (unansweredQuestions.length > 0) {
        performAIAnalysis(unansweredQuestions);
      }
    }
  }, [visibleQuestions, companyData, configData]);

  const loadQuestionsByProvider = (provider) => {
    let questionsToLoad = [];

    if (provider === 'Azure') {
      // Load Azure questions - flatten sections into questions array
      if (azureQuestionsData.sections) {
        azureQuestionsData.sections.forEach((section) => {
          // Add section as a header
          questionsToLoad.push({
            id: `section_${section.title}`,
            type: 'section',
            title: section.title
          });
          // Add all questions from this section
          questionsToLoad.push(...section.questions.map(q => ({
            ...q,
            question: q.text, // Map 'text' to 'question' for consistency
            type: 'single' // Azure questions are single-choice based on the structure
          })));
        });
      }
    } else {
      // Default to AWS questions
      questionsToLoad = awsQuestionsData.questions || [];
    }

    setQuestions(questionsToLoad);
  };

  const loadSessionData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load session messages to get company info
      const sessionResponse = await axios.get(`${API_BASE_URL}/api/sessions/${sessionId}`);

      // Find the detailed company info from messages
      const messages = sessionResponse.data.messages || [];
      const detailedMessage = messages.find(
        msg => msg.role === 'assistant' && msg.content?.mode === 'detailed_info'
      );

      if (!detailedMessage) {
        setError('No company information found. Please complete the company search first.');
        return;
      }

      setCompanyData(detailedMessage.content.data);

      // Load configuration
      const configResponse = await axios.get(`${API_BASE_URL}/api/sessions/${sessionId}/config`);
      setConfigData(configResponse.data.configuration);

      // Load any saved questionnaire answers
      try {
        const answersResponse = await axios.get(
          `${API_BASE_URL}/api/sessions/${sessionId}/questionnaire`
        );
        if (answersResponse.data.answers) {
          setAnswers(answersResponse.data.answers);
        }
        if (answersResponse.data.ai_predictions) {
          setAiPredictions(answersResponse.data.ai_predictions);
        }
        if (answersResponse.data.ai_assumptions) {
          setAiAssumptions(answersResponse.data.ai_assumptions);
        }
      } catch (err) {
        // No saved answers yet, that's okay
        console.log('No saved questionnaire data');
      }

    } catch (err) {
      console.error('Error loading session data:', err);
      setError('Failed to load session data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const computeVisibleQuestions = () => {
    const visible = [];
    const visited = new Set();

    const traverse = (questionId) => {
      if (!questionId || visited.has(questionId)) return;
      visited.add(questionId);

      const question = questions.find((q) => q.id === questionId);
      if (!question) return;

      visible.push(questionId);

      // For sections, just add them and move on
      if (question.type === 'section') {
        return;
      }

      // Check if this question has a selected answer
      const answer = answers[questionId];

      if (question.type === 'single' && answer) {
        // Find the selected option
        const selectedOption = question.options?.find(opt =>
          opt.label === answer || opt.value === answer
        );
        if (selectedOption?.next) {
          selectedOption.next.forEach(traverse);
        }
      } else if (question.type === 'multi' && Array.isArray(answer) && answer.length > 0) {
        // For multi-select, check all selected options for next questions
        const selectedOptions = question.options?.filter(opt =>
          answer.includes(opt.label) || answer.includes(opt.value)
        ) || [];
        selectedOptions.forEach(opt => {
          if (opt.next) {
            opt.next.forEach(traverse);
          }
        });
      } else if (question.type === 'input' && answer) {
        // Input questions can have next
        if (question.next) {
          question.next.forEach(traverse);
        }
      }

      // If question has unconditional next (not tied to options), traverse them
      if (question.next && (question.type === 'input' || question.type === 'section')) {
        question.next.forEach(traverse);
      }
    };

    // Start with root questions (those not referenced in any 'next' or those marked with show: true)
    const allNextIds = new Set();
    questions.forEach((q) => {
      if (q.next) {
        q.next.forEach(id => allNextIds.add(id));
      }
      if (q.options) {
        q.options.forEach(opt => {
          if (opt.next) {
            opt.next.forEach(id => allNextIds.add(id));
          }
        });
      }
    });

    // For Azure questions, also check the 'show' property and 'parent' property
    const rootQuestions = questions.filter(q => {
      // Sections are always root
      if (q.type === 'section') return true;

      // Questions with show: true and no parent are root
      if (q.show === true && !q.parent) return true;

      // Questions not referenced in any 'next' are root
      if (!allNextIds.has(q.id) && q.show !== false) return true;

      return false;
    });

    rootQuestions.forEach(q => traverse(q.id));

    setVisibleQuestions(visible);
  };

  const performAIAnalysis = async (questionIds) => {
    if (analyzing) return;

    try {
      setAnalyzing(true);

      const response = await axios.post(`${API_BASE_URL}/api/questionnaire/predict`, {
        session_id: sessionId,
        question_ids: questionIds,
        company_data: companyData,
        configuration: configData,
        current_answers: answers,
      });

      if (response.data.predictions) {
        // Merge new predictions with existing ones
        setAiPredictions(prev => ({ ...prev, ...response.data.predictions }));

        // Apply predictions to answers (auto-preselect)
        const newAnswers = { ...answers };
        Object.entries(response.data.predictions).forEach(([qId, prediction]) => {
          if (prediction && !answers[qId]) {
            newAnswers[qId] = prediction;
          }
        });
        setAnswers(newAnswers);

        // Store AI assumptions
        if (response.data.assumptions) {
          setAiAssumptions(prev => ({ ...prev, ...response.data.assumptions }));

          // Expand assumptions by default
          const newExpanded = { ...expandedAssumptions };
          questionIds.forEach(qId => {
            newExpanded[qId] = true;
          });
          setExpandedAssumptions(newExpanded);
        }

        // Save progress
        await saveProgress(newAnswers, response.data.predictions, response.data.assumptions);
      }
    } catch (err) {
      console.error('Error performing AI analysis:', err);
      // Don't show error to user, just log it
    } finally {
      setAnalyzing(false);
    }
  };

  const saveProgress = async (currentAnswers, currentPredictions, currentAssumptions) => {
    try {
      await axios.post(`${API_BASE_URL}/api/questionnaire/save`, {
        session_id: sessionId,
        answers: currentAnswers,
        ai_predictions: currentPredictions,
        ai_assumptions: currentAssumptions,
      });
    } catch (err) {
      console.error('Error saving progress:', err);
    }
  };

  const handleAnswerChange = (questionId, value, isMulti = false) => {
    const question = questions.find(q => q.id === questionId);
    const oldAnswer = answers[questionId];

    // Update answer
    const newAnswers = { ...answers };

    if (isMulti) {
      const currentValues = newAnswers[questionId] || [];
      if (currentValues.includes(value)) {
        // Remove if already selected
        newAnswers[questionId] = currentValues.filter(v => v !== value);
      } else {
        // Add to selection
        newAnswers[questionId] = [...currentValues, value];
      }
    } else {
      newAnswers[questionId] = value;
    }

    // Check if answer changed in a way that affects child questions
    const answerChanged = JSON.stringify(oldAnswer) !== JSON.stringify(newAnswers[questionId]);

    if (answerChanged) {
      // Find all questions that should be cleared (children of this question)
      const questionsToCheck = [questionId];
      const childQuestions = new Set();

      while (questionsToCheck.length > 0) {
        const currentQId = questionsToCheck.shift();
        const currentQ = questions.find(q => q.id === currentQId);

        if (!currentQ) continue;

        // Get next questions from this question
        const nextQIds = [];
        if (currentQ.next) {
          nextQIds.push(...currentQ.next);
        }
        if (currentQ.options) {
          currentQ.options.forEach(opt => {
            if (opt.next) {
              nextQIds.push(...opt.next);
            }
          });
        }

        nextQIds.forEach(qId => {
          if (!childQuestions.has(qId)) {
            childQuestions.add(qId);
            questionsToCheck.push(qId);
          }
        });
      }

      // Clear answers for child questions
      childQuestions.forEach(qId => {
        delete newAnswers[qId];
      });
    }

    setAnswers(newAnswers);
    saveProgress(newAnswers, aiPredictions, aiAssumptions);
  };

  const toggleAssumption = (questionId) => {
    setExpandedAssumptions(prev => ({
      ...prev,
      [questionId]: !prev[questionId]
    }));
  };

  const handleSubmit = async () => {
    try {
      setGeneratingSummary(true);
      setError(null);

      const response = await axios.post(`${API_BASE_URL}/api/questionnaire/submit`, {
        session_id: sessionId,
        answers: answers,
        company_data: companyData,
        configuration: configData,
      });

      // Navigate to summary or show summary in modal
      alert('Questionnaire submitted successfully! Summary will be generated.');
      console.log('Summary:', response.data.summary);

    } catch (err) {
      console.error('Error submitting questionnaire:', err);
      setError('Failed to submit questionnaire. Please try again.');
    } finally {
      setGeneratingSummary(false);
    }
  };

  const renderQuestion = (questionId) => {
    const question = questions.find(q => q.id === questionId);
    if (!question) return null;

    // Render section headers
    if (question.type === 'section') {
      return (
        <div key={question.id} className="question-section-header">
          <h2>{question.title}</h2>
        </div>
      );
    }

    const hasAssumption = aiAssumptions[questionId];
    const isExpanded = expandedAssumptions[questionId] !== false; // Default expanded

    return (
      <div key={question.id} className="question-card">
        {/* AI Assumptions Dropdown */}
        {hasAssumption && (
          <div className="ai-assumptions">
            <button
              className="assumptions-toggle"
              onClick={() => toggleAssumption(question.id)}
            >
              <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
              <span className="toggle-label">AI Assumptions</span>
            </button>
            {isExpanded && (
              <div className="assumptions-content">
                <p>{aiAssumptions[question.id]}</p>
              </div>
            )}
          </div>
        )}

        {/* Question */}
        <div className="question-content">
          <h3 className="question-text">{question.question}</h3>

          {/* Single choice */}
          {question.type === 'single' && (
            <div className="options-container">
              {question.options.map((option, idx) => {
                const optionValue = option.value || option.label;
                const optionLabel = option.label;
                return (
                  <label key={idx} className="option-label radio-option">
                    <input
                      type="radio"
                      name={question.id}
                      value={optionValue}
                      checked={answers[question.id] === optionValue || answers[question.id] === optionLabel}
                      onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                    />
                    <span>{optionLabel}</span>
                  </label>
                );
              })}
            </div>
          )}

          {/* Multiple choice */}
          {question.type === 'multi' && (
            <div className="options-container">
              {question.options.map((option, idx) => {
                const optionValue = option.value || option.label;
                const optionLabel = option.label;
                return (
                  <label key={idx} className="option-label checkbox-option">
                    <input
                      type="checkbox"
                      value={optionValue}
                      checked={(answers[question.id] || []).includes(optionValue) || (answers[question.id] || []).includes(optionLabel)}
                      onChange={() => handleAnswerChange(question.id, optionValue, true)}
                    />
                    <span>{optionLabel}</span>
                  </label>
                );
              })}
            </div>
          )}

          {/* Input */}
          {question.type === 'input' && (
            <input
              type="text"
              className="text-input"
              value={answers[question.id] || ''}
              onChange={(e) => handleAnswerChange(question.id, e.target.value)}
              placeholder="Enter your answer..."
            />
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="questionnaire-loading">
        <div className="loading-spinner"></div>
        <p>Loading questionnaire...</p>
      </div>
    );
  }

  if (generatingSummary) {
    return (
      <div className="questionnaire-loading">
        <div className="loading-spinner"></div>
        <p>Generating summary...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="questionnaire-error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')} className="back-button">
          Back to Chat
        </button>
      </div>
    );
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>Landing Zone Questionnaire</h1>
        <p className="company-info-header">
          {companyData?.['Company name']} - {configData?.cloud_provider}
        </p>
        <button onClick={() => navigate('/')} className="back-link">
          ← Back to Chat
        </button>
      </div>

      <div className="questionnaire-content">
        {analyzing && (
          <div className="analyzing-banner">
            <div className="analyzing-spinner"></div>
            <span>AI is analyzing questions...</span>
          </div>
        )}

        <div className="questions-list">
          {visibleQuestions.map(renderQuestion)}
        </div>

        <div className="questionnaire-footer">
          <button
            onClick={handleSubmit}
            className="submit-button"
            disabled={loading || analyzing || generatingSummary}
          >
            Submit & Generate Summary
          </button>
        </div>
      </div>
    </div>
  );
}

export default Questionnaire;
