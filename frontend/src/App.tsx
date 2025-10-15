import React, { useState } from 'react';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface Candidate {
  applicant_id: string;
  name: string;
  age: number;
  gender: string;
  education: string;
  experience_years: number;
  passage_text: string;
  skills: string[];
  industries: string[];
  years: number;
}

interface SearchResult {
  _id: string;
  _score: number;
  _source: Candidate;
  highlight?: {
    passage_text?: string[];
  };
}

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `${API_BASE}/search/hybrid?q=${encodeURIComponent(query)}`
      );

      if (!response.ok) {
        throw new Error('검색에 실패했습니다');
      }

      const data = await response.json();
      setResults(data.hits?.hits || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎯 채용 AI 검색 시스템</h1>
        <p>하이브리드 검색 (키워드 + 시맨틱 벡터)</p>
      </header>

      <main className="App-main">
        <div className="search-container">
          <div className="search-box">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="검색어를 입력하세요 (예: Python 개발자, 5년 경력, 금융권)"
              className="search-input"
              disabled={loading}
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="search-button"
            >
              {loading ? '🔍 검색 중...' : '🔍 검색'}
            </button>
          </div>

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
        </div>

        <div className="results-container">
          {results.length > 0 && (
            <div className="results-header">
              <h2>📋 검색 결과 ({results.length}건)</h2>
            </div>
          )}

          <div className="results-list">
            {results.map((result) => (
              <div key={result._id} className="result-card">
                <div className="candidate-header">
                  <div className="candidate-info">
                    <h3 className="candidate-name">{result._source.name || '이름 없음'}</h3>
                    <div className="candidate-basic">
                      <span className="info-badge">ID: {result._source.applicant_id}</span>
                      <span className="info-badge">{result._source.age}세</span>
                      <span className="info-badge">{result._source.gender}</span>
                      <span className="info-badge">경력 {result._source.experience_years}년</span>
                    </div>
                  </div>
                  <div className="match-score">
                    <div className="score-value">{result._score.toFixed(1)}</div>
                    <div className="score-label">매칭도</div>
                  </div>
                </div>

                <div className="candidate-details">
                  <div className="detail-row">
                    <span className="detail-label">🎓 학력:</span>
                    <span className="detail-value">{result._source.education || '정보 없음'}</span>
                  </div>
                </div>

                <div className="candidate-description">
                  <strong>📝 경력 요약:</strong>
                  {result.highlight?.passage_text ? (
                    <div
                      className="highlight-text"
                      dangerouslySetInnerHTML={{
                        __html: result.highlight.passage_text.join(' ... ')
                      }}
                    />
                  ) : (
                    <p className="passage-text">{result._source.passage_text}</p>
                  )}
                </div>

                <div className="candidate-tags">
                  {result._source.skills && result._source.skills.length > 0 && (
                    <div className="tag-group">
                      <strong>💼 보유 스킬:</strong>
                      <div className="tags">
                        {result._source.skills.map((skill, idx) => (
                          <span key={idx} className="tag tag-skill">{skill}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {result._source.industries && result._source.industries.length > 0 && (
                    <div className="tag-group">
                      <strong>🏢 산업 분야:</strong>
                      <div className="tags">
                        {result._source.industries.map((industry, idx) => (
                          <span key={idx} className="tag tag-industry">{industry}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {!loading && results.length === 0 && query && (
            <div className="no-results">
              <p>💭 검색 결과가 없습니다.</p>
              <p className="hint">다른 키워드로 검색해보세요.</p>
            </div>
          )}

          {!loading && !query && (
            <div className="welcome-message">
              <h3>👋 환영합니다!</h3>
              <p>위 검색창에 원하는 조건을 입력하세요.</p>
              <div className="example-queries">
                <p><strong>검색 예시:</strong></p>
                <ul>
                  <li>Python 개발 경험이 있는 지원자</li>
                  <li>금융권 근무 경력 5년 이상</li>
                  <li>React, TypeScript 가능한 프론트엔드 개발자</li>
                  <li>리더십 역량이 뛰어난 인재</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="App-footer">
        <p>Recruit AI Starter - OpenSearch Hybrid Search + LLM API</p>
      </footer>
    </div>
  );
}

export default App;