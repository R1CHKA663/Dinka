import React, { useState, useEffect, createContext, useContext, useRef, useMemo } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation, Navigate, useParams } from "react-router-dom";
import axios from "axios";
import { Toaster, toast } from "sonner";
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Components
const Header = () => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [onlineCount, setOnlineCount] = useState(250);
  const navigate = useNavigate();
  const location = useLocation();

  // Fetch fake online count
  useEffect(() => {
    const fetchOnline = async () => {
      try {
        const res = await api.get('/online');
        if (res.data.success) setOnlineCount(res.data.online);
      } catch (e) {
        setOnlineCount(200 + Math.floor(Math.random() * 200));
      }
    };
    fetchOnline();
    const interval = setInterval(fetchOnline, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <header className="header" data-testid="header">
      <div className="header-content">
        <Link to="/" className="logo" data-testid="logo-link">
          <img src="/logo.png" alt="EASY MONEY" className="logo-img" />
          <span className="logo-text">EASY MONEY</span>
        </Link>
        
        <div className="online-counter" data-testid="online-counter">
          <span className="online-dot"></span>
          <span className="online-count">{onlineCount} онлайн</span>
        </div>
        
        <nav className={`nav ${menuOpen ? 'open' : ''}`} data-testid="nav-menu">
          <Link to="/" className="nav-link" data-testid="nav-home">Главная</Link>
          <Link to="/mines" className="nav-link" data-testid="nav-mines">Mines</Link>
          <Link to="/dice" className="nav-link" data-testid="nav-dice">Dice</Link>
          <Link to="/tower" className="nav-link" data-testid="nav-tower">Tower</Link>
          <Link to="/slots" className="nav-link" data-testid="nav-slots" style={{color: '#f59e0b'}}>🎰 Слоты</Link>
          {user && <Link to="/bonus" className="nav-link" data-testid="nav-bonus">Бонусы</Link>}
          {user && <Link to="/ref" className="nav-link" data-testid="nav-ref">Партнёрка</Link>}
          <a href="https://t.me/easymoneycaspro" target="_blank" rel="noopener noreferrer" className="nav-link tg-link" data-testid="nav-telegram">
            <i className="fa-brands fa-telegram"></i> Telegram
          </a>
        </nav>

        <div className="header-right">
          {user ? (
            <>
              <div className="balance-box" data-testid="balance-box">
                <span className="balance-amount">{user.balance?.toFixed(2)} ₽</span>
                <button className="btn-deposit" onClick={() => navigate('/wallet')} data-testid="deposit-btn">
                  <i className="fa-solid fa-wallet"></i>
                </button>
              </div>
              <div className="user-menu" data-testid="user-menu">
                <img src={user.img || "/logo.png"} alt="" className="user-avatar" />
                <div className="user-dropdown">
                  <span className="user-name">{user.name}</span>
                  <Link to="/wallet" className="dropdown-item">Кошелёк</Link>
                  <Link to="/ref" className="dropdown-item">Партнёрка</Link>
                  <button onClick={logout} className="dropdown-item logout" data-testid="logout-btn">Выход</button>
                </div>
              </div>
            </>
          ) : (
            <button className="btn-auth" onClick={() => navigate('/login')} data-testid="login-btn">
              <i className="fa-brands fa-telegram"></i> Войти
            </button>
          )}
          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} data-testid="menu-toggle">
            <i className="fa-solid fa-ellipsis-vertical"></i>
          </button>
        </div>
      </div>
      
      {/* Fullscreen Navigation Menu */}
      {menuOpen && (
        <div className="fullscreen-menu" data-testid="fullscreen-menu">
          <div className="fullscreen-menu-header">
            <span className="menu-title">Навигация</span>
            <button className="close-menu" onClick={() => setMenuOpen(false)}>
              <i className="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div className="fullscreen-menu-content">
            <div className="menu-section">
              <div className="menu-section-title">Игры</div>
              <Link to="/mines" className="menu-item" data-testid="menu-mines">
                <i className="fa-solid fa-bomb"></i>
                <span>Mines</span>
              </Link>
              <Link to="/dice" className="menu-item" data-testid="menu-dice">
                <i className="fa-solid fa-dice"></i>
                <span>Dice</span>
              </Link>
              <Link to="/tower" className="menu-item" data-testid="menu-tower">
                <i className="fa-solid fa-tower-observation"></i>
                <span>Tower</span>
              </Link>
              <Link to="/crash" className="menu-item" data-testid="menu-crash">
                <i className="fa-solid fa-chart-line"></i>
                <span>Crash</span>
              </Link>
              <Link to="/bubbles" className="menu-item" data-testid="menu-bubbles">
                <i className="fa-solid fa-circle"></i>
                <span>Bubbles</span>
              </Link>
              <Link to="/x100" className="menu-item" data-testid="menu-x100">
                <i className="fa-solid fa-bolt"></i>
                <span>X100</span>
              </Link>
            </div>
            
            <div className="menu-section">
              <div className="menu-section-title">Аккаунт</div>
              {user ? (
                <>
                  <Link to="/wallet" className="menu-item" data-testid="menu-wallet">
                    <i className="fa-solid fa-wallet"></i>
                    <span>Кошелёк</span>
                  </Link>
                  <Link to="/bonus" className="menu-item" data-testid="menu-bonus">
                    <i className="fa-solid fa-gift"></i>
                    <span>Бонусы</span>
                  </Link>
                  <Link to="/ref" className="menu-item" data-testid="menu-ref">
                    <i className="fa-solid fa-users"></i>
                    <span>Партнёрка</span>
                  </Link>
                  <Link to="/support" className="menu-item" data-testid="menu-support">
                    <i className="fa-solid fa-headset"></i>
                    <span>Поддержка</span>
                  </Link>
                </>
              ) : (
                <Link to="/login" className="menu-item" data-testid="menu-login">
                  <i className="fa-brands fa-telegram"></i>
                  <span>Войти через Telegram</span>
                </Link>
              )}
            </div>
            
            <div className="menu-section">
              <div className="menu-section-title">Информация</div>
              <a href="https://t.me/easymoneycaspro" target="_blank" rel="noopener noreferrer" className="menu-item">
                <i className="fa-brands fa-telegram"></i>
                <span>Telegram канал</span>
              </a>
              <Link to="/" className="menu-item" data-testid="menu-home">
                <i className="fa-solid fa-house"></i>
                <span>Главная</span>
              </Link>
            </div>
            
            {user && (
              <button onClick={() => { logout(); setMenuOpen(false); }} className="menu-logout-btn" data-testid="menu-logout">
                <i className="fa-solid fa-right-from-bracket"></i>
                <span>Выйти из аккаунта</span>
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
};

const Footer = () => (
  <footer className="footer" data-testid="footer">
    <div className="footer-content">
      <div className="footer-logo">
        <img src="/logo.png" alt="EASY MONEY" />
        <span>EASY MONEY</span>
      </div>
      <div className="footer-links">
        <a href="https://t.me/easymoneycaspro" target="_blank" rel="noopener noreferrer">
          <i className="fa-brands fa-telegram"></i> Telegram
        </a>
        <Link to="/policy"><i className="fa-solid fa-shield-halved"></i> Политика конфиденциальности</Link>
        <Link to="/terms"><i className="fa-solid fa-file-contract"></i> Пользовательское соглашение</Link>
      </div>
      <div className="footer-copy">© 2025 EASY MONEY. Все права защищены.</div>
    </div>
  </footer>
);

const GameHistory = () => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get('/history/recent?limit=15');
        if (res.data.success) setHistory(res.data.history);
      } catch (e) {}
    };
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const gameIcons = { 
    mines: 'fa-bomb', 
    dice: 'fa-dice', 
    bubbles: 'fa-circle', 
    tower: 'fa-tower-observation',
    x100: 'fa-circle-notch',
    crash: 'fa-rocket'
  };
  const gameNames = { 
    mines: 'Mines', 
    dice: 'Dice', 
    bubbles: 'Bubbles', 
    tower: 'Tower',
    x100: 'X100',
    crash: 'Crash'
  };

  return (
    <div className="game-history" data-testid="game-history">
      <h3><i className="fa-solid fa-clock-rotate-left"></i> История игр</h3>
      <div className="history-list">
        {history.map((h, i) => (
          <div key={i} className={`history-item ${h.status}`} data-testid={`history-item-${i}`}>
            <div className="history-row-top">
              <div className="history-game">
                <i className={`fa-solid ${gameIcons[h.game] || 'fa-gamepad'}`}></i>
                <span>{gameNames[h.game] || h.game}</span>
              </div>
              <div className="history-bet">{h.bet?.toFixed(2)} ₽</div>
            </div>
            <div className="history-row-bottom">
              <div className="history-coeff">x{h.coefficient?.toFixed ? h.coefficient.toFixed(2) : h.coefficient}</div>
              <div className={`history-result ${h.status}`}>
                {h.status === 'win' ? `+${h.win?.toFixed(2)}` : '0.00'} ₽
              </div>
            </div>
            <div className="history-user-desktop">{h.name?.split(' ')[0]}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Pages
const Home = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const games = [
    { id: 'mines', name: 'Mines', img: '/assets/images/games/mines.jpg', desc: 'Найди все алмазы и избегай бомб!', color: '#d4a853' },
    { id: 'dice', name: 'Dice', img: '/assets/images/games/dice.jpg', desc: 'Угадай число и выиграй!', color: '#3b82f6' },
    { id: 'bubbles', name: 'Bubbles', img: '/assets/images/games/bubbles.jpg', desc: 'Поймай свой множитель!', color: '#8b5cf6' },
    { id: 'tower', name: 'Tower', img: '/assets/images/games/tower.jpg', desc: 'Проложи путь к вершине! До 500x!', color: '#f59e0b' },
    { id: 'crash', name: 'Crash', img: '/assets/images/games/crash.jpg', desc: 'Успей забрать до краша!', color: '#ef4444' },
    { id: 'x100', name: 'X100', img: '/assets/images/games/x100.jpg', desc: 'Поймай x100 множитель!', color: '#ec4899' }
  ];

  return (
    <div className="page home-page" data-testid="home-page">
      <div className="hero">
        <img src="/logo.png" alt="EASY MONEY" className="hero-logo" />
        <h1>EASY MONEY</h1>
        <p>Играй и выигрывай! Лучшие игры с честным RTP</p>
        {!user && (
          <button className="btn-hero" onClick={() => navigate('/login')} data-testid="hero-login-btn">
            <i className="fa-brands fa-telegram"></i> Начать играть
          </button>
        )}
      </div>

      <div className="games-grid" data-testid="games-grid">
        {games.map(g => (
          <div 
            key={g.id} 
            className={`game-card ${g.comingSoon ? 'coming-soon' : ''}`} 
            onClick={() => !g.comingSoon && navigate(`/${g.id}`)} 
            data-testid={`game-card-${g.id}`}
          >
            <img src={g.img} alt={g.name} className="game-card-img" />
          </div>
        ))}
      </div>

      <GameHistory />
      
      {/* Players Chat Button */}
      <PlayersChat />
    </div>
  );
};

// ==================== PLAYERS CHAT ====================
const PlayersChat = () => {
  const { user, updateBalance } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  
  useEffect(() => {
    if (isOpen) {
      loadMessages();
      const interval = setInterval(loadMessages, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const loadMessages = async () => {
    try {
      const res = await api.get('/chat/messages');
      if (res.data.success) {
        // Filter private messages
        const filtered = res.data.messages.filter(m => 
          !m.private_for || m.private_for === user?.id
        );
        setMessages(filtered);
      }
    } catch (e) {}
  };
  
  const sendMessage = async () => {
    if (!newMessage.trim() || !user) return;
    
    setLoading(true);
    try {
      const res = await api.post('/chat/send', { text: newMessage });
      if (res.data.success) {
        setNewMessage('');
        if (res.data.balance !== undefined) {
          updateBalance(res.data.balance);
        }
        await loadMessages();
        toast.success('Сообщение отправлено!');
      } else {
        toast.error(res.data.error || 'Ошибка');
      }
    } catch (e) {
      // Сообщение все равно отправилось, просто показываем успех
      setNewMessage('');
      await loadMessages();
      toast.success('Сообщение отправлено!');
    }
    setLoading(false);
  };
  
  const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };
  
  if (!user) return null;
  
  return (
    <>
      <button 
        className="players-chat-btn"
        onClick={() => setIsOpen(!isOpen)}
        data-testid="players-chat-btn"
      >
        <i className="fa-solid fa-comments"></i>
        {isOpen ? '' : <span>Чат</span>}
      </button>
      
      {isOpen && (
        <div className="players-chat" data-testid="players-chat">
          <div className="players-chat-header">
            <h4><i className="fa-solid fa-users"></i> Чат игроков</h4>
            <button onClick={() => setIsOpen(false)}>
              <i className="fa-solid fa-times"></i>
            </button>
          </div>
          
          <div className="players-chat-commands">
            <span onClick={() => setNewMessage('/stats')}>/stats</span>
            <span onClick={() => setNewMessage('/send @')}>💸 Отправить</span>
            <span onClick={() => setNewMessage('/request ')}>🙏 Запрос</span>
            <span onClick={() => setNewMessage('/help')}>❓ Помощь</span>
          </div>
          
          <div className="players-chat-messages">
            {messages.length === 0 ? (
              <div className="no-messages">
                <i className="fa-solid fa-message"></i>
                <p>Начните общение!</p>
              </div>
            ) : (
              messages.map(msg => (
                <div 
                  key={msg.id} 
                  className={`chat-message ${msg.type} ${msg.user_id === user?.id ? 'own' : ''} ${msg.user_id === 'system' ? 'system' : ''}`}
                >
                  <div className="message-header">
                    <span className="message-user">{msg.user_name}</span>
                    <span className="message-time">{formatTime(msg.created_at)}</span>
                  </div>
                  <div className="message-text">{msg.text}</div>
                  {msg.type === 'request' && msg.user_id !== user?.id && (
                    <button 
                      className="btn-donate"
                      onClick={() => setNewMessage(`/send @${msg.user_name} ${msg.request_amount}`)}
                    >
                      💰 Помочь {msg.request_amount}₽
                    </button>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="players-chat-input">
            <input
              type="text"
              value={newMessage}
              onChange={e => setNewMessage(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && sendMessage()}
              placeholder={user?.is_demo ? "Только для верифицированных..." : "Сообщение или /команда..."}
              disabled={loading || user?.is_demo}
            />
            <button onClick={sendMessage} disabled={loading || !newMessage.trim() || user?.is_demo}>
              <i className="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);

  // Get refCode from URL or localStorage
  const refCode = new URLSearchParams(location.search).get('ref') || localStorage.getItem('ref_code');
  
  // Save ref_code to localStorage immediately if present in URL
  useEffect(() => {
    const urlRefCode = new URLSearchParams(location.search).get('ref');
    if (urlRefCode) {
      localStorage.setItem('ref_code', urlRefCode);
    }
  }, [location.search]);

  useEffect(() => {
    // Define global callback for Telegram Widget
    window.onTelegramAuth = async (tgUser) => {
      setLoading(true);
      try {
        // IMPORTANT: Read ref_code directly from localStorage at the moment of auth
        // to avoid closure issues with stale refCode value
        const currentRefCode = localStorage.getItem('ref_code');
        console.log('🔍 TG Auth: ref_code from localStorage:', currentRefCode);
        
        const res = await api.post('/auth/telegram', { 
          id: tgUser.id,
          first_name: tgUser.first_name,
          last_name: tgUser.last_name || '',
          username: tgUser.username || '',
          photo_url: tgUser.photo_url || '',
          auth_date: tgUser.auth_date,
          hash: tgUser.hash,
          ref_code: currentRefCode 
        });
        if (res.data.success) {
          login(res.data.token, res.data.user);
          toast.success('Добро пожаловать!');
          navigate('/');
        }
      } catch (e) {
        toast.error(e.response?.data?.detail || 'Ошибка авторизации');
      }
      setLoading(false);
    };

    // Load Telegram Widget script
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', 'easymoneycas_bot');
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '10');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');
    script.async = true;

    const container = document.getElementById('telegram-login-container');
    if (container) {
      container.innerHTML = '';
      container.appendChild(script);
    }

    return () => {
      delete window.onTelegramAuth;
    };
  }, [login, navigate]);

  const handleDemoLogin = async () => {
    setLoading(true);
    try {
      // Read ref_code directly from localStorage to avoid closure issues
      const currentRefCode = localStorage.getItem('ref_code');
      console.log('🔍 Demo Auth: ref_code from localStorage:', currentRefCode);
      
      const username = `player_${Math.random().toString(36).substr(2, 6)}`;
      const res = await api.post('/auth/demo', {
        username: username,
        ref_code: currentRefCode
      });
      if (res.data.success) {
        login(res.data.token, res.data.user);
        toast.success('Добро пожаловать!');
        navigate('/');
      }
    } catch (e) {
      toast.error('Ошибка входа');
    }
    setLoading(false);
  };

  return (
    <div className="page login-page" data-testid="login-page">
      <div className="login-card">
        <img src="/logo.png" alt="EASY MONEY" className="login-logo" />
        <h2>Вход в EASY MONEY</h2>
        <p>Авторизуйтесь через Telegram для начала игры</p>
        
        <div id="telegram-login-container" className="telegram-widget" data-testid="telegram-widget">
          {/* Telegram Widget will be inserted here */}
        </div>

        <div className="login-divider"><span>или</span></div>

        <button className="btn-demo" onClick={handleDemoLogin} disabled={loading} data-testid="demo-login-btn">
          {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-play"></i>}
          Демо режим (с балансом 1000₽)
        </button>

        <p className="login-note">
          <i className="fa-solid fa-shield"></i> Безопасная авторизация через Telegram
        </p>
      </div>
    </div>
  );
};

const MinesGame = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [bet, setBet] = useState(10);
  const [bombs, setBombs] = useState(5);
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cells, setCells] = useState(Array(25).fill({ status: 'hidden', type: null }));

  useEffect(() => {
    if (user) checkActiveGame();
  }, [user]);

  const checkActiveGame = async () => {
    try {
      const res = await api.get('/games/mines/current');
      if (res.data.success && res.data.active) {
        setGame(res.data);
        const newCells = Array(25).fill({ status: 'hidden', type: null });
        res.data.clicked?.forEach(c => {
          newCells[c - 1] = { status: 'opened', type: 'safe' };
        });
        setCells(newCells);
      }
    } catch (e) {}
  };

  const startGame = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    
    setLoading(true);
    try {
      const res = await api.post('/games/mines/play', { bet, bombs });
      if (res.data.success) {
        setGame({ active: true, bet, bombs, win: 0, clicked: [] });
        setCells(Array(25).fill({ status: 'hidden', type: null }));
        updateBalance(res.data.balance);
        toast.success('Игра началась!');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const pressCell = async (index) => {
    if (!game?.active || cells[index].status !== 'hidden') return;
    
    setLoading(true);
    try {
      const res = await api.post('/games/mines/press', { cell: index + 1 });
      if (res.data.success) {
        const newCells = [...cells];
        
        if (res.data.status === 'lose') {
          newCells[index] = { status: 'opened', type: 'bomb' };
          res.data.mines?.forEach(m => {
            if (m !== index + 1) newCells[m - 1] = { status: 'revealed', type: 'bomb' };
          });
          res.data.win_positions?.forEach(p => {
            newCells[p - 1] = { status: 'revealed', type: 'safe' };
          });
          setGame(null);
          toast.error('Бум! Вы проиграли');
        } else if (res.data.status === 'finish') {
          newCells[index] = { status: 'opened', type: 'safe' };
          res.data.mines?.forEach(m => {
            newCells[m - 1] = { status: 'revealed', type: 'bomb' };
          });
          setGame(null);
          updateBalance(res.data.balance);
          toast.success(`Победа! +${res.data.win?.toFixed(2)}₽`);
        } else {
          newCells[index] = { status: 'opened', type: 'safe' };
          setGame(prev => ({ ...prev, win: res.data.win, clicked: res.data.clicked }));
        }
        setCells(newCells);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const takeWin = async () => {
    if (!game?.active || game.win <= 0) return;
    
    setLoading(true);
    try {
      const res = await api.post('/games/mines/take');
      if (res.data.success) {
        const newCells = [...cells];
        res.data.mines?.forEach(m => {
          newCells[m - 1] = { status: 'revealed', type: 'bomb' };
        });
        res.data.win_positions?.forEach(p => {
          if (newCells[p - 1].status === 'hidden') newCells[p - 1] = { status: 'revealed', type: 'safe' };
        });
        setCells(newCells);
        setGame(null);
        updateBalance(res.data.balance);
        toast.success(`Вы забрали ${res.data.win?.toFixed(2)}₽!`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  return (
    <div className="page game-page mines-page" data-testid="mines-page">
      <div className="game-container">
        <div className="game-board mines-board" data-testid="mines-board">
          {cells.map((cell, i) => (
            <button
              key={i}
              className={`mines-cell ${cell.status} ${cell.type || ''}`}
              onClick={() => pressCell(i)}
              disabled={!game?.active || cell.status !== 'hidden' || loading}
              data-testid={`mines-cell-${i}`}
            >
              {cell.status !== 'hidden' && (
                cell.type === 'bomb' ? <i className="fa-solid fa-bomb"></i> : <i className="fa-solid fa-gem"></i>
              )}
            </button>
          ))}
        </div>

        <div className="game-controls" data-testid="mines-controls">
          <h2><i className="fa-solid fa-bomb"></i> Mines</h2>
          
          {!game?.active ? (
            <>
              <div className="control-group">
                <label>Ставка</label>
                <div className="bet-input">
                  <button onClick={() => setBet(Math.max(1, bet / 2))}>½</button>
                  <input type="number" value={bet} onChange={e => setBet(Math.max(1, +e.target.value))} data-testid="mines-bet-input" />
                  <button onClick={() => setBet(Math.min(user?.balance || 1000, bet * 2))}>×2</button>
                </div>
              </div>

              <div className="control-group">
                <label>Бомб: {bombs}</label>
                <input type="range" min="2" max="24" value={bombs} onChange={e => setBombs(+e.target.value)} data-testid="mines-bombs-slider" />
              </div>

              <button className="btn-start" onClick={startGame} disabled={loading} data-testid="mines-start-btn">
                {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : 'Начать игру'}
              </button>
            </>
          ) : (
            <>
              <div className="game-info">
                <div className="info-item">
                  <span>Ставка</span>
                  <strong>{game.bet?.toFixed(2)} ₽</strong>
                </div>
                <div className="info-item">
                  <span>Бомб</span>
                  <strong>{game.bombs}</strong>
                </div>
                <div className="info-item highlight">
                  <span>Выигрыш</span>
                  <strong>{game.win?.toFixed(2)} ₽</strong>
                </div>
              </div>

              <button className="btn-take" onClick={takeWin} disabled={loading || game.win <= 0} data-testid="mines-take-btn">
                {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : `Забрать ${game.win?.toFixed(2)} ₽`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const DiceGame = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [bet, setBet] = useState(10);
  const [chance, setChance] = useState(50);
  const [direction, setDirection] = useState('under');  // 'under' or 'over'
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [animatedResult, setAnimatedResult] = useState(null);
  const [animating, setAnimating] = useState(false);

  // Coefficient based on chance
  const coefficient = (99 / chance).toFixed(2);
  
  // Threshold: for 'under' = chance, for 'over' = 100 - chance
  const threshold = direction === 'under' ? chance : (100 - chance);

  const play = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    
    setLoading(true);
    setResult(null);
    setAnimating(true);
    
    try {
      const res = await api.post('/games/dice/play', { bet, chance, type: direction });
      
      if (res.data.success) {
        // Animate rolling numbers
        const finalResult = res.data.roll;
        let counter = 0;
        const maxIterations = 20;
        
        const animateRoll = () => {
          counter++;
          const randomNum = Math.floor(Math.random() * 100);
          setAnimatedResult(randomNum);
          
          if (counter < maxIterations) {
            setTimeout(animateRoll, 50 + counter * 10);
          } else {
            // Show final result
            setAnimatedResult(finalResult);
            setAnimating(false);
            setResult(res.data);
            updateBalance(res.data.balance);
            
            if (res.data.win > 0) {
              toast.success(`🎲 Победа! +${res.data.win?.toFixed(2)}₽ (x${res.data.multiplier})`);
            } else {
              toast.error('🎲 Не повезло!');
            }
            setLoading(false);
          }
        };
        
        animateRoll();
      } else {
        setAnimating(false);
        setLoading(false);
      }
    } catch (e) {
      setAnimating(false);
      toast.error(e.response?.data?.detail || 'Ошибка');
      setLoading(false);
    }
  };

  // Determine win/lose based on result
  const isWin = result && result.win > 0;

  return (
    <div className="page game-page dice-page" data-testid="dice-page">
      <div className="game-container">
        <div className="game-board dice-board" data-testid="dice-board">
          <div className="dice-display">
            <div className="dice-bar">
              {/* Under zone (left side) */}
              <div 
                className={`dice-zone ${direction === 'under' ? 'active win-zone' : 'lose-zone'}`} 
                style={{ width: `${chance}%` }}
              >
                {direction === 'under' && <span className="zone-label">ВЫИГРЫШ</span>}
              </div>
              {/* Over zone (right side) */}
              <div 
                className={`dice-zone ${direction === 'over' ? 'active win-zone' : 'lose-zone'}`} 
                style={{ width: `${100 - chance}%` }}
              >
                {direction === 'over' && <span className="zone-label">ВЫИГРЫШ</span>}
              </div>
              {/* Result marker */}
              {(animatedResult !== null || result) && (
                <div 
                  className={`dice-marker ${result ? (isWin ? 'win' : 'lose') : ''} ${animating ? 'animating' : ''}`} 
                  style={{ left: `${animatedResult !== null ? animatedResult : (result?.roll || 50)}%` }}
                >
                  {animatedResult !== null ? animatedResult : result?.roll}
                </div>
              )}
              {/* Threshold indicator */}
              <div className="dice-threshold" style={{ left: `${chance}%` }}>
                <span>{chance}</span>
              </div>
            </div>
            <div className="dice-labels">
              <span>0</span>
              <span style={{ position: 'absolute', left: `${chance}%`, transform: 'translateX(-50%)' }}>{chance}</span>
              <span>99</span>
            </div>
          </div>
          
          {result && !animating && (
            <div className={`dice-result ${isWin ? 'win' : 'lose'}`} data-testid="dice-result">
              <div className="result-number">{result.roll}</div>
              <div className="result-text">
                {isWin ? `+${result.win?.toFixed(2)} ₽` : 'Проигрыш'}
              </div>
              <div className="result-info">
                {direction === 'under' ? `Меньше ${chance}` : `Больше ${chance}`} — {isWin ? 'Угадал!' : 'Не угадал'}
              </div>
            </div>
          )}
        </div>

        <div className="game-controls" data-testid="dice-controls">
          <h2><i className="fa-solid fa-dice"></i> Dice</h2>
          
          <div className="control-group">
            <label>Ставка</label>
            <div className="bet-input">
              <button onClick={() => setBet(Math.max(1, bet / 2))} disabled={loading}>½</button>
              <input type="number" value={bet} onChange={e => setBet(Math.max(1, +e.target.value))} disabled={loading} data-testid="dice-bet-input" />
              <button onClick={() => setBet(Math.min(user?.balance || 1000, bet * 2))} disabled={loading}>×2</button>
            </div>
          </div>

          <div className="control-group">
            <label>Шанс: {chance}% | Множитель: x{coefficient}</label>
            <input 
              type="range" 
              min="2" 
              max="98" 
              value={chance} 
              onChange={e => setChance(+e.target.value)} 
              disabled={loading}
              data-testid="dice-chance-slider" 
            />
          </div>

          <div className="control-group direction-btns">
            <button 
              className={`dice-dir-btn ${direction === 'under' ? 'active' : ''}`} 
              onClick={() => !loading && setDirection('under')} 
              disabled={loading}
              data-testid="dice-under-btn"
            >
              <i className="fa-solid fa-arrow-down"></i> 
              <span>Меньше {chance}</span>
            </button>
            <button 
              className={`dice-dir-btn ${direction === 'over' ? 'active' : ''}`} 
              onClick={() => !loading && setDirection('over')} 
              disabled={loading}
              data-testid="dice-over-btn"
            >
              <i className="fa-solid fa-arrow-up"></i> 
              <span>Больше {chance}</span>
            </button>
          </div>

          <button className="btn-start" onClick={play} disabled={loading} data-testid="dice-play-btn">
            {loading ? (
              animating ? <><i className="fa-solid fa-dice fa-spin"></i> Бросок...</> : <i className="fa-solid fa-spinner fa-spin"></i>
            ) : (
              <><i className="fa-solid fa-dice"></i> Бросить</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const BubblesGame = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [bet, setBet] = useState(10);
  const [target, setTarget] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [currentMult, setCurrentMult] = useState(1.0);
  const [animating, setAnimating] = useState(false);
  const [bubbleSize, setBubbleSize] = useState(50);

  const play = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    
    setLoading(true);
    setAnimating(true);
    setResult(null);
    setCurrentMult(1.0);
    setBubbleSize(50);
    
    try {
      const res = await api.post('/games/bubbles/play', { bet, target });
      
      if (res.data.success) {
        const finalMult = res.data.result;
        let mult = 1.0;
        
        const animate = () => {
          mult += 0.03 * (1 + mult * 0.02);
          const newMult = parseFloat(Math.min(mult, finalMult).toFixed(2));
          setCurrentMult(newMult);
          setBubbleSize(50 + newMult * 25);
          
          if (mult >= finalMult) {
            setAnimating(false);
            setResult(res.data);
            updateBalance(res.data.balance);
            
            if (res.data.status === 'win') {
              toast.success(`🎉 Лопнул на x${target}! +${res.data.win?.toFixed(2)}₽`);
            } else {
              toast.error(`💥 Пузырь лопнул на x${newMult}!`);
            }
            setLoading(false);
          } else {
            setTimeout(animate, 40);
          }
        };
        animate();
      }
    } catch (e) {
      setAnimating(false);
      toast.error(e.response?.data?.detail || 'Ошибка');
      setLoading(false);
    }
  };

  return (
    <div className="page game-page bubbles-page" data-testid="bubbles-page">
      <div className="game-container">
        <div className="game-board bubbles-board" data-testid="bubbles-board">
          <div className="bubbles-display">
            {/* Animated bubble */}
            <div 
              className={`bubble ${animating ? 'inflating' : ''} ${result?.status === 'lose' ? 'popped' : ''}`}
              style={{ 
                width: `${bubbleSize}%`,
                height: `${bubbleSize}%`,
                background: result?.status === 'lose' 
                  ? 'radial-gradient(circle at 30% 30%, #ef4444, #991b1b)'
                  : result?.status === 'win'
                  ? 'radial-gradient(circle at 30% 30%, #d4a853, #b8923e)'
                  : 'radial-gradient(circle at 30% 30%, #60a5fa, #2563eb, #1d4ed8)',
                boxShadow: `0 0 ${bubbleSize/2}px rgba(96, 165, 250, 0.4), inset 0 0 30px rgba(255,255,255,0.2)`
              }}
            >
              <div className="bubble-reflection"></div>
              <div className="bubble-mult">x{currentMult.toFixed(2)}</div>
            </div>
            
            {/* Target line */}
            <div className="target-line" style={{ bottom: `${Math.min(target * 10, 90)}%` }}>
              <span>Цель: x{target}</span>
            </div>
          </div>
        </div>
        
        <div className="game-controls" data-testid="bubbles-controls">
          <h2><i className="fa-solid fa-circle"></i> Bubbles</h2>
          
          <div className="control-group">
            <label>Цель: x{target.toFixed(2)}</label>
            <input 
              type="range" 
              min="1.1" 
              max="100" 
              step="0.1" 
              value={target} 
              onChange={e => setTarget(+e.target.value)} 
              disabled={loading}
            />
          </div>
          
          <div className="quick-targets">
            {[1.5, 2, 3, 5, 10].map(t => (
              <button 
                key={t} 
                onClick={() => setTarget(t)} 
                className={target === t ? 'active' : ''} 
                disabled={loading}
              >
                x{t}
              </button>
            ))}
          </div>
          
          <div className="control-group">
            <label>Ставка</label>
            <div className="bet-input">
              <button onClick={() => setBet(Math.max(1, bet / 2))} disabled={loading}>½</button>
              <input type="number" value={bet} onChange={e => setBet(Math.max(1, +e.target.value))} disabled={loading} data-testid="bubbles-bet-input" />
              <button onClick={() => setBet(Math.min(user?.balance || 1000, bet * 2))} disabled={loading}>×2</button>
            </div>
          </div>
          
          <div className="potential-win">
            Потенциальный выигрыш: <strong>{(bet * target).toFixed(2)} ₽</strong>
          </div>
          
          <button className="btn-start" onClick={play} disabled={loading} data-testid="bubbles-play-btn">
            {loading ? (
              animating ? <><i className="fa-solid fa-circle fa-beat-fade"></i> Надувается...</> : <i className="fa-solid fa-spinner fa-spin"></i>
            ) : 'Надуть пузырь'}
          </button>
        </div>
      </div>
    </div>
  );
};


// ==================== TOWER GAME ====================

const TowerGame = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  
  const [bet, setBet] = useState(10);
  const [difficulty, setDifficulty] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [gameActive, setGameActive] = useState(false);
  const [currentRow, setCurrentRow] = useState(0);
  const [path, setPath] = useState([]);
  const [currentWin, setCurrentWin] = useState(0);
  const [bombs, setBombs] = useState(null);
  const [gameOver, setGameOver] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [config, setConfig] = useState(null);
  const [characterPos, setCharacterPos] = useState({ row: 0, col: 0 });
  const [animatingTo, setAnimatingTo] = useState(null);
  const [showExplosion, setShowExplosion] = useState(null);
  
  // Load config
  useEffect(() => {
    api.get('/games/tower/config').then(res => {
      if (res.data.success) {
        setConfig(res.data);
      }
    }).catch(() => {});
    
    // Check for active game
    api.get('/games/tower/current').then(res => {
      if (res.data.success && res.data.active) {
        setGameActive(true);
        setCurrentRow(res.data.current_row);
        setPath(res.data.path || []);
        setCurrentWin(res.data.win);
        setBet(res.data.bet);
        setDifficulty(res.data.difficulty);
        if (res.data.path && res.data.path.length > 0) {
          const lastStep = res.data.path[res.data.path.length - 1];
          setCharacterPos({ row: lastStep.row, col: lastStep.column });
        }
      }
    }).catch(() => {});
  }, []);
  
  const getMultiplier = (row) => {
    if (!config) return 1;
    return config.multipliers[difficulty]?.[row] || 1;
  };
  
  const getBombsPerRow = () => {
    if (difficulty === 'high') return 3;
    if (difficulty === 'medium') return 2;
    return 1;
  };
  
  const startGame = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    if (gameActive) return;
    
    setLoading(true);
    try {
      const res = await api.post('/games/tower/start', { bet, difficulty });
      if (res.data.success) {
        updateBalance(res.data.balance);
        setGameActive(true);
        setCurrentRow(0);
        setPath([]);
        setCurrentWin(0);
        setBombs(null);
        setGameOver(false);
        setLastResult(null);
        setCharacterPos({ row: 0, col: 0 });
        setShowExplosion(null);
        toast.success('Игра начата! Выберите безопасный путь');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };
  
  const makeStep = async (column) => {
    if (!gameActive || loading || gameOver) return;
    if (currentRow >= 9) return;
    
    setLoading(true);
    setAnimatingTo({ row: currentRow + 1, col: column });
    
    try {
      const res = await api.post('/games/tower/step', { column });
      
      // Animate character movement
      await new Promise(resolve => setTimeout(resolve, 300));
      setCharacterPos({ row: res.data.row, col: column });
      
      if (res.data.status === 'lose') {
        // Show explosion
        setShowExplosion({ row: res.data.row, col: column });
        await new Promise(resolve => setTimeout(resolve, 500));
        
        setBombs(res.data.bombs);
        setGameOver(true);
        setGameActive(false);
        setLastResult({ status: 'lose', message: res.data.message });
        toast.error('💥 ' + res.data.message);
      } else if (res.data.status === 'win') {
        // Reached the top!
        setBombs(res.data.bombs);
        setCurrentRow(res.data.row);
        setPath(prev => [...prev, { row: res.data.row, column }]);
        setCurrentWin(res.data.win);
        updateBalance(res.data.balance);
        setGameOver(true);
        setGameActive(false);
        setLastResult({ status: 'win', win: res.data.win, message: res.data.message });
        toast.success('🎉 ' + res.data.message);
      } else {
        // Continue
        setCurrentRow(res.data.row);
        setPath(res.data.path);
        setCurrentWin(res.data.win);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    
    setLoading(false);
    setAnimatingTo(null);
  };
  
  const cashout = async () => {
    if (!gameActive || loading || currentRow < 1) return;
    
    setLoading(true);
    try {
      const res = await api.post('/games/tower/cashout');
      if (res.data.success) {
        updateBalance(res.data.balance);
        setBombs(res.data.bombs);
        setGameOver(true);
        setGameActive(false);
        setLastResult({ status: 'cashout', win: res.data.win, message: res.data.message });
        toast.success('💰 ' + res.data.message);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };
  
  const isStepInPath = (row, col) => {
    return path.some(p => p.row === row && p.column === col);
  };
  
  const isBomb = (row, col) => {
    if (!bombs) return false;
    return bombs[String(row)]?.includes(col);
  };
  
  const renderCell = (row, col) => {
    const inPath = isStepInPath(row, col);
    const isBombCell = gameOver && isBomb(row, col);
    const isCharHere = characterPos.row === row && characterPos.col === col && !gameOver;
    const isClickable = gameActive && !gameOver && row === currentRow + 1;
    const isExploding = showExplosion?.row === row && showExplosion?.col === col;
    
    return (
      <div 
        key={`${row}-${col}`}
        className={`tower-cell ${inPath ? 'safe' : ''} ${isBombCell ? 'bomb' : ''} ${isClickable ? 'clickable' : ''} ${isExploding ? 'exploding' : ''}`}
        onClick={() => isClickable && makeStep(col)}
        data-testid={`tower-cell-${row}-${col}`}
      >
        {isCharHere && (
          <div className="tower-character">
            <i className="fa-solid fa-person-walking"></i>
          </div>
        )}
        {inPath && !isCharHere && (
          <div className="tower-footprint">
            <i className="fa-solid fa-shoe-prints"></i>
          </div>
        )}
        {isBombCell && (
          <div className="tower-bomb">
            <i className="fa-solid fa-bomb"></i>
          </div>
        )}
        {isExploding && (
          <div className="tower-explosion">
            <i className="fa-solid fa-explosion"></i>
          </div>
        )}
        {gameOver && !isBombCell && !inPath && row <= 9 && (
          <div className="tower-gem">
            <i className="fa-solid fa-gem"></i>
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className="page game-page tower-page" data-testid="tower-page">
      <div className="tower-layout">
        {/* Game Board */}
        <div className="tower-board-container">
          <div className="tower-board">
            {/* Rows from 9 (top) to 1 (bottom) */}
            {[9, 8, 7, 6, 5, 4, 3, 2, 1].map(row => (
              <div key={row} className="tower-row">
                <div className="tower-row-multiplier">
                  <span className={`multiplier ${row <= currentRow ? 'passed' : row === currentRow + 1 ? 'next' : ''}`}>
                    x{getMultiplier(row)}
                  </span>
                </div>
                <div className="tower-cells">
                  {[1, 2, 3, 4].map(col => renderCell(row, col))}
                </div>
              </div>
            ))}
            {/* Start row */}
            <div className="tower-row start-row">
              <div className="tower-row-multiplier">
                <span className="multiplier start">СТАРТ</span>
              </div>
              <div className="tower-cells start-cells">
                <div className="tower-start-zone">
                  {!gameActive && !characterPos.row && (
                    <div className="tower-character idle">
                      <i className="fa-solid fa-person"></i>
                    </div>
                  )}
                  <span>Начало пути</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Result overlay */}
          {lastResult && (
            <div className={`tower-result-overlay ${lastResult.status}`}>
              <div className="result-content">
                {lastResult.status === 'lose' ? (
                  <>
                    <i className="fa-solid fa-skull"></i>
                    <h3>Игра окончена!</h3>
                    <p>Вы наступили на бомбу</p>
                  </>
                ) : (
                  <>
                    <i className="fa-solid fa-trophy"></i>
                    <h3>{lastResult.status === 'win' ? 'Вершина!' : 'Забрали!'}</h3>
                    <p className="win-amount">+{lastResult.win?.toFixed(2)}₽</p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Controls */}
        <div className="tower-controls">
          <h2><i className="fa-solid fa-tower-observation"></i> Башня</h2>
          
          <div className="control-group">
            <label>Ставка</label>
            <div className="bet-input">
              <button onClick={() => setBet(Math.max(1, bet / 2))} disabled={gameActive}>½</button>
              <input 
                type="number" 
                value={bet} 
                onChange={e => setBet(Math.max(1, parseFloat(e.target.value) || 1))}
                disabled={gameActive}
                data-testid="tower-bet"
              />
              <button onClick={() => setBet(Math.min(user?.balance || 1000, bet * 2))} disabled={gameActive}>x2</button>
            </div>
          </div>
          
          <div className="control-group">
            <label>Сложность ({getBombsPerRow()} бомб в ряду)</label>
            <div className="difficulty-buttons">
              {[
                { key: 'low', label: 'Легко', bombs: 1 },
                { key: 'medium', label: 'Средне', bombs: 2 },
                { key: 'high', label: 'Сложно', bombs: 3 }
              ].map(d => (
                <button 
                  key={d.key}
                  className={difficulty === d.key ? 'active' : ''}
                  onClick={() => !gameActive && setDifficulty(d.key)}
                  disabled={gameActive}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
          
          {gameActive && currentRow > 0 && (
            <div className="current-win-display">
              <span className="label">Текущий выигрыш:</span>
              <span className="amount">{currentWin.toFixed(2)}₽</span>
              <span className="multiplier">x{getMultiplier(currentRow)}</span>
            </div>
          )}
          
          <div className="play-buttons">
            {!gameActive ? (
              <button 
                className="btn-play"
                onClick={startGame}
                disabled={loading || !user}
                data-testid="tower-play-btn"
              >
                {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : (
                  <>
                    <i className="fa-solid fa-play"></i> Играть
                  </>
                )}
              </button>
            ) : (
              <button 
                className="btn-cashout"
                onClick={cashout}
                disabled={loading || currentRow < 1}
                data-testid="tower-cashout-btn"
              >
                {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : (
                  <>
                    <i className="fa-solid fa-hand-holding-dollar"></i> 
                    Забрать {currentWin.toFixed(2)}₽
                  </>
                )}
              </button>
            )}
          </div>
          
          {gameActive && (
            <div className="tower-hint">
              <i className="fa-solid fa-circle-info"></i>
              <span>Выберите безопасную клетку в следующем ряду</span>
            </div>
          )}
          
          {/* Multipliers table */}
          {config && (
            <div className="multipliers-table">
              <h4>Множители</h4>
              <div className="table-rows">
                {[9, 8, 7, 6, 5, 4, 3, 2, 1].map(row => (
                  <div key={row} className={`table-row ${row === currentRow + 1 ? 'next' : row <= currentRow ? 'passed' : ''}`}>
                    <span className="row-num">Ряд {row}</span>
                    <span className="row-mult">x{getMultiplier(row)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== SLOTS PAGE ====================

const Wallet = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState('deposit');
  const [amount, setAmount] = useState(150);
  const [wallet, setWallet] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState({ payments: [], withdraws: [] });
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [selectedMethod, setSelectedMethod] = useState('sbp');
  const [promoCode, setPromoCode] = useState('');
  const [withdrawSystem, setWithdrawSystem] = useState('card');
  const [withdrawProvider, setWithdrawProvider] = useState('fiat');
  const [bankName, setBankName] = useState('');
  const [cryptoNetwork, setCryptoNetwork] = useState('');

  const isDemo = user?.is_demo;

  useEffect(() => {
    fetchProviders();  // Always load providers
    if (!isDemo) {
      fetchHistory();
    }
  }, [isDemo]);

  const fetchProviders = async () => {
    try {
      const res = await api.get('/payment/providers');
      if (res.data.success && res.data.providers.length > 0) {
        setProviders(res.data.providers);
        setSelectedProvider(res.data.providers[0]);
        // Method will be selected on payment gateway
      }
    } catch (e) {
      console.error('Error fetching providers:', e);
    }
  };

  const fetchHistory = async () => {
    try {
      const [payments, withdraws] = await Promise.all([
        api.get('/payment/history'),
        api.get('/withdraw/history')
      ]);
      setHistory({
        payments: payments.data.payments || [],
        withdraws: withdraws.data.withdraws || []
      });
    } catch (e) {}
  };

  const createPayment = async () => {
    if (isDemo) {
      toast.error('Пополнение недоступно в демо-режиме');
      return;
    }
    if (!selectedProvider) {
      toast.error('Выберите платёжную систему');
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post('/payment/create', { 
        amount, 
        provider: selectedProvider.id,
        method: 'auto',  // Method will be selected on payment gateway
        promo_code: promoCode
      });
      
      // For admin deposits, open Telegram
      if (res.data.success && res.data.is_admin_deposit) {
        const telegramUsername = res.data.contact || '@easymoneysupportvip';
        const telegramUrl = `https://t.me/${telegramUsername.replace('@', '')}`;
        toast.success(res.data.message || 'Свяжитесь с администратором');
        window.open(telegramUrl, '_blank');
      } else if (res.data.success && res.data.payment_url) {
        toast.success('Перенаправление на оплату...');
        window.location.href = res.data.payment_url;
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка создания платежа');
    }
    setLoading(false);
  };

  const createWithdraw = async () => {
    if (isDemo) {
      toast.error('Вывод недоступен в демо-режиме');
      return;
    }
    if (!wallet) return toast.error('Введите реквизиты');
    if (amount < 150) return toast.error('Минимум: 150₽');
    if (withdrawProvider === 'fiat' && !bankName) return toast.error('Выберите банк');
    if (withdrawProvider !== 'fiat' && !cryptoNetwork) return toast.error('Выберите сеть');
    
    setLoading(true);
    try {
      const res = await api.post('/withdraw/create', { 
        amount, 
        wallet, 
        system: withdrawSystem,
        provider: withdrawProvider === 'fiat' ? '1plat' : withdrawProvider,
        bank_name: bankName,
        crypto_network: cryptoNetwork
      });
      if (res.data.success) {
        const me = await api.get('/auth/me');
        if (me.data.success) updateBalance(me.data.user.balance);
        toast.success(res.data.message || 'Заявка создана!');
        fetchHistory();
        setWallet('');
        setBankName('');
        setCryptoNetwork('');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  // Group providers by type
  const fiatProviders = providers.filter(p => !p.id.includes('crypto'));
  const cryptoProviders = providers.filter(p => p.id.includes('crypto'));

  return (
    <div className="page wallet-page" data-testid="wallet-page">
      <div className="wallet-card">
        <h2><i className="fa-solid fa-wallet"></i> Кошелёк</h2>
        
        {isDemo && (
          <div className="demo-warning" data-testid="demo-warning">
            <i className="fa-solid fa-exclamation-triangle"></i>
            <div>
              <strong>Демо-режим</strong>
              <p>Для пополнения и вывода авторизуйтесь через Telegram.</p>
              <button className="btn-telegram" onClick={() => navigate('/login')}>
                <i className="fa-brands fa-telegram"></i> Войти
              </button>
            </div>
          </div>
        )}
        
        <div className="wallet-balance">
          <span>Баланс {isDemo && '(демо)'}</span>
          <strong>{user?.balance?.toFixed(2)} ₽</strong>
        </div>

        <div className="wallet-tabs">
          <button className={tab === 'deposit' ? 'active' : ''} onClick={() => setTab('deposit')}>Пополнить</button>
          <button className={tab === 'withdraw' ? 'active' : ''} onClick={() => setTab('withdraw')}>Вывести</button>
        </div>

        {tab === 'deposit' ? (
          <div className="wallet-form" data-testid="deposit-form">
            {/* Provider selection with icons */}
            <div className="form-group">
              <label>Платёжная система</label>
              <div className="provider-grid">
                {providers.map(p => (
                  <button 
                    key={p.id}
                    className={`provider-btn ${selectedProvider?.id === p.id ? 'active' : ''}`}
                    onClick={() => setSelectedProvider(p)}
                    disabled={isDemo}
                  >
                    {p.id === 'cryptobot' ? (
                      <i className="fa-brands fa-telegram"></i>
                    ) : p.id === 'cryptocloud' ? (
                      <i className="fa-brands fa-bitcoin"></i>
                    ) : (
                      <i className={`fa-solid ${p.icon}`}></i>
                    )}
                    <span>{p.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Method selection removed - user chooses on payment gateway */}

            {/* Amount */}
            <div className="form-group">
              <label>Сумма</label>
              <input 
                type="number" 
                value={amount} 
                onChange={e => setAmount(+e.target.value)} 
                min="100" 
                disabled={isDemo}
                data-testid="deposit-amount" 
              />
            </div>
            <div className="quick-amounts">
              {[100, 500, 1000, 5000].map(a => (
                <button key={a} onClick={() => setAmount(a)} disabled={isDemo}>{a}₽</button>
              ))}
            </div>

            {/* Promo code */}
            <div className="form-group">
              <label>Промокод (если есть)</label>
              <input 
                type="text" 
                value={promoCode} 
                onChange={e => setPromoCode(e.target.value)} 
                placeholder="Введите промокод"
                disabled={isDemo}
                data-testid="deposit-promo" 
              />
            </div>

            <button 
              className="btn-submit" 
              onClick={createPayment} 
              disabled={loading || amount < 100 || isDemo || !selectedProvider}
              data-testid="deposit-submit"
            >
              {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : 
               isDemo ? 'Недоступно в демо' : `Пополнить ${amount}₽`}
            </button>
          </div>
        ) : (
          <div className="wallet-form" data-testid="withdraw-form">
            {/* Withdraw provider selection */}
            <div className="form-group">
              <label>Способ вывода</label>
              <div className="provider-grid">
                <button 
                  className={`provider-btn ${withdrawProvider === 'fiat' ? 'active' : ''}`}
                  onClick={() => { setWithdrawProvider('fiat'); setWithdrawSystem('card'); }}
                  disabled={isDemo}
                >
                  <i className="fa-solid fa-credit-card"></i>
                  <span>Карта/СБП</span>
                </button>
                <button 
                  className={`provider-btn ${withdrawProvider === 'cryptobot' ? 'active' : ''}`}
                  onClick={() => { setWithdrawProvider('cryptobot'); setWithdrawSystem('usdt'); }}
                  disabled={isDemo}
                >
                  <i className="fa-brands fa-telegram"></i>
                  <span>CryptoBot</span>
                </button>
                <button 
                  className={`provider-btn ${withdrawProvider === 'crypto' ? 'active' : ''}`}
                  onClick={() => { setWithdrawProvider('crypto'); setWithdrawSystem('usdt'); }}
                  disabled={isDemo}
                >
                  <i className="fa-brands fa-bitcoin"></i>
                  <span>Crypto</span>
                </button>
              </div>
            </div>
            
            {/* Fiat methods */}
            {withdrawProvider === 'fiat' && (
              <div className="form-group">
                <label>Метод</label>
                <div className="method-grid">
                  {['card', 'sbp'].map(m => (
                    <button 
                      key={m}
                      className={`method-btn ${withdrawSystem === m ? 'active' : ''}`}
                      onClick={() => setWithdrawSystem(m)}
                      disabled={isDemo}
                    >
                      {m === 'sbp' ? 'СБП' : 'Карта'}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Crypto methods - CryptoBot */}
            {withdrawProvider === 'cryptobot' && (
              <div className="form-group">
                <label>Криптовалюта</label>
                <div className="method-grid">
                  {['usdt', 'ton', 'btc', 'eth'].map(m => (
                    <button 
                      key={m}
                      className={`method-btn ${withdrawSystem === m ? 'active' : ''}`}
                      onClick={() => setWithdrawSystem(m)}
                      disabled={isDemo}
                    >
                      {m.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Crypto methods - Crypto with more options */}
            {withdrawProvider === 'crypto' && (
              <div className="form-group">
                <label>Криптовалюта <span className="crypto-hint">(прокрутите для выбора)</span></label>
                <div className="method-grid crypto-scroll">
                  {['usdt', 'btc', 'eth', 'ltc', 'doge', 'trx', 'xrp', 'bnb', 'sol', 'matic', 'avax', 'dash', 'xmr', 'shib'].map(m => (
                    <button 
                      key={m}
                      className={`method-btn ${withdrawSystem === m ? 'active' : ''} ${['usdt', 'btc', 'eth'].includes(m) ? 'popular' : ''}`}
                      onClick={() => setWithdrawSystem(m)}
                      disabled={isDemo}
                    >
                      {m.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            <div className="form-group">
              <label>Сумма (мин. 150₽)</label>
              <input 
                type="number" 
                value={amount} 
                onChange={e => setAmount(+e.target.value)} 
                min="150" 
                disabled={isDemo}
                data-testid="withdraw-amount" 
              />
            </div>
            
            <div className="form-group">
              <label>
                {withdrawProvider === 'fiat' 
                  ? (withdrawSystem === 'sbp' ? 'Телефон' : 'Номер карты')
                  : (withdrawProvider === 'cryptobot' ? 'Telegram ID' : 'Кошелёк')}
              </label>
              <input 
                type="text" 
                value={wallet} 
                onChange={e => setWallet(e.target.value)} 
                placeholder={
                  withdrawProvider === 'fiat' 
                    ? (withdrawSystem === 'sbp' ? '+7 999 123 45 67' : '1234 5678 9012 3456')
                    : (withdrawProvider === 'cryptobot' ? '123456789' : 'TRC20/ERC20 адрес')
                }
                disabled={isDemo}
                data-testid="withdraw-wallet" 
              />
            </div>
            
            {/* Bank name for fiat withdrawals */}
            {withdrawProvider === 'fiat' && (
              <div className="form-group">
                <label>Название банка</label>
                <select 
                  value={bankName || ''} 
                  onChange={e => setBankName(e.target.value)}
                  disabled={isDemo}
                  data-testid="withdraw-bank"
                  className="bank-select"
                >
                  <option value="">Выберите банк</option>
                  <option value="Сбербанк">Сбербанк</option>
                  <option value="Тинькофф">Тинькофф</option>
                  <option value="Альфа-Банк">Альфа-Банк</option>
                  <option value="ВТБ">ВТБ</option>
                  <option value="Газпромбанк">Газпромбанк</option>
                  <option value="Райффайзен">Райффайзен</option>
                  <option value="Открытие">Открытие</option>
                  <option value="Росбанк">Росбанк</option>
                  <option value="Почта Банк">Почта Банк</option>
                  <option value="МТС Банк">МТС Банк</option>
                  <option value="Промсвязьбанк">Промсвязьбанк</option>
                  <option value="Совкомбанк">Совкомбанк</option>
                  <option value="Россельхозбанк">Россельхозбанк</option>
                  <option value="Уралсиб">Уралсиб</option>
                  <option value="Ак Барс">Ак Барс</option>
                  <option value="Хоум Кредит">Хоум Кредит</option>
                  <option value="Ренессанс Кредит">Ренессанс Кредит</option>
                  <option value="Юникредит">Юникредит</option>
                  <option value="Сити Банк">Сити Банк</option>
                  <option value="БКС Банк">БКС Банк</option>
                  <option value="Авангард">Авангард</option>
                  <option value="Русский Стандарт">Русский Стандарт</option>
                  <option value="ОТП Банк">ОТП Банк</option>
                  <option value="Банк Санкт-Петербург">Банк Санкт-Петербург</option>
                  <option value="Банк Зенит">Банк Зенит</option>
                  <option value="Локо-Банк">Локо-Банк</option>
                  <option value="Восточный Банк">Восточный Банк</option>
                  <option value="СДМ-Банк">СДМ-Банк</option>
                  <option value="РНКБ">РНКБ</option>
                  <option value="Банк Москвы">Банк Москвы</option>
                  <option value="ДелоБанк">ДелоБанк</option>
                  <option value="Экспобанк">Экспобанк</option>
                  <option value="Другой">Другой</option>
                </select>
              </div>
            )}
            
            {withdrawProvider !== 'fiat' && (
              <div className="input-group">
                <label>Сеть</label>
                <select 
                  value={cryptoNetwork || ''} 
                  onChange={e => setCryptoNetwork(e.target.value)}
                  disabled={isDemo}
                  data-testid="withdraw-network"
                  className="network-select"
                >
                  <option value="">Выберите сеть</option>
                  <option value="TRC20">TRC20 (Tron)</option>
                  <option value="ERC20">ERC20 (Ethereum)</option>
                  <option value="BEP20">BEP20 (BSC)</option>
                  <option value="TON">TON</option>
                  <option value="Bitcoin">Bitcoin</option>
                  <option value="Solana">Solana</option>
                  <option value="Polygon">Polygon</option>
                  <option value="Arbitrum">Arbitrum</option>
                </select>
              </div>
            )}
            
            {withdrawProvider !== 'fiat' && (
              <p className="crypto-note">
                <i className="fa-solid fa-info-circle"></i> Крипто выводы обрабатываются вручную (1-24ч)
              </p>
            )}
            
            {user?.wager > 0 && !isDemo && (
              <p className="wallet-warning">
                <i className="fa-solid fa-exclamation-triangle"></i> 
                Отыграйте вейджер: {user.wager?.toFixed(2)}₽
              </p>
            )}
            
            <button 
              className="btn-submit" 
              onClick={createWithdraw} 
              disabled={loading || amount < 150 || user?.wager > 0 || isDemo}
              data-testid="withdraw-submit"
            >
              {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : 
               isDemo ? 'Недоступно в демо' : `Вывести ${amount}₽`}
            </button>
          </div>
        )}

        {!isDemo && (
          <div className="wallet-history">
            <h3>История</h3>
            {(tab === 'deposit' ? history.payments : history.withdraws).length === 0 ? (
              <p className="no-history">Нет операций</p>
            ) : (
              (tab === 'deposit' ? history.payments : history.withdraws).map((item, i) => (
                <div key={i} className={`history-item ${item.status}`}>
                  <span>{item.amount?.toFixed(2)}₽</span>
                  <span className="status">
                    {item.status === 'completed' ? '✓ Выполнен' : 
                     item.status === 'pending' ? '⏳ Ожидание' : 
                     item.status === 'processing' ? '⚙️ Обработка' : '✗ Отклонён'}
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Payment Success Page - redirects to home
const PaymentSuccess = () => {
  const navigate = useNavigate();
  const { updateBalance } = useAuth();
  const [countdown, setCountdown] = useState(5);
  
  useEffect(() => {
    // Update user balance when page loads
    const fetchUser = async () => {
      try {
        const res = await api.get('/auth/me');
        if (res.data.success) {
          updateBalance(res.data.user.balance);
        }
      } catch (e) {
        console.error('Error updating balance:', e);
      }
    };
    fetchUser();
  }, [updateBalance]);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, [navigate]);
  
  return (
    <div className="page payment-result-page" data-testid="payment-success-page">
      <div className="payment-result-card success">
        <div className="result-icon success">
          <i className="fa-solid fa-check-circle"></i>
        </div>
        <h2>Оплата прошла успешно!</h2>
        <p>Ваш баланс пополнен. Спасибо за пополнение!</p>
        <div className="result-redirect">
          <span>Перенаправление на главную через {countdown}...</span>
        </div>
        <button className="btn-result" onClick={() => navigate('/')}>
          <i className="fa-solid fa-house"></i> На главную
        </button>
      </div>
    </div>
  );
};

// Payment Failed Page
const PaymentFailed = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const errorMessage = searchParams.get('error') || 'Произошла ошибка при обработке платежа';
  const errorCode = searchParams.get('code') || '';
  
  return (
    <div className="page payment-result-page" data-testid="payment-failed-page">
      <div className="payment-result-card failed">
        <div className="result-icon failed">
          <i className="fa-solid fa-times-circle"></i>
        </div>
        <h2>Оплата не прошла</h2>
        <p className="error-message">{errorMessage}</p>
        {errorCode && <p className="error-code">Код ошибки: {errorCode}</p>}
        
        <div className="result-info">
          <h4><i className="fa-solid fa-info-circle"></i> Возможные причины:</h4>
          <ul>
            <li>Недостаточно средств на карте/кошельке</li>
            <li>Карта заблокирована или истёк срок действия</li>
            <li>Превышен лимит операций</li>
            <li>Технические проблемы на стороне платёжной системы</li>
            <li>Операция отклонена банком</li>
          </ul>
        </div>
        
        <div className="result-actions">
          <button className="btn-result primary" onClick={() => navigate('/wallet')}>
            <i className="fa-solid fa-rotate-right"></i> Попробовать снова
          </button>
          <button className="btn-result secondary" onClick={() => navigate('/')}>
            <i className="fa-solid fa-house"></i> На главную
          </button>
        </div>
        
        <div className="result-support">
          <p>Если проблема повторяется, обратитесь в поддержку:</p>
          <a href="https://t.me/easymoneycas_bot" target="_blank" rel="noopener noreferrer" className="support-link">
            <i className="fa-brands fa-telegram"></i> Написать в Telegram
          </a>
        </div>
      </div>
    </div>
  );
};

const Bonus = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [cashbackData, setCashbackData] = useState({ raceback: 0, level: null, next_level: null, levels: [], total_deposited: 0 });
  const [promoCode, setPromoCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [dailyBonus, setDailyBonus] = useState(null);
  const [achievements, setAchievements] = useState([]);
  const [dailyTasks, setDailyTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('bonuses');

  const isDemo = user?.is_demo;

  useEffect(() => {
    fetchCashback();
    fetchDailyBonus();
    fetchAchievements();
    fetchDailyTasks();
  }, []);

  const fetchCashback = async () => {
    try {
      const res = await api.get('/bonus/raceback');
      if (res.data.success) {
        setCashbackData({
          raceback: res.data.raceback || 0,
          level: res.data.level || { name: "Бронза", percent: 5, min_deposit: 0 },
          next_level: res.data.next_level,
          levels: res.data.levels || [],
          total_deposited: res.data.total_deposited || 0
        });
      }
    } catch (e) {}
  };

  const fetchDailyTasks = async () => {
    try {
      const res = await api.get('/tasks/daily');
      if (res.data.success) setDailyTasks(res.data.tasks || []);
    } catch (e) {}
  };

  const claimDailyTask = async (taskId) => {
    if (isDemo) {
      toast.error('Задания недоступны в демо-режиме');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post(`/tasks/daily/${taskId}/claim`);
      if (res.data.success) {
        updateBalance(res.data.balance);
        toast.success(`🎯 ${res.data.message}`);
        fetchDailyTasks();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const fetchDailyBonus = async () => {
    try {
      const res = await api.get('/bonus/daily');
      if (res.data.success) setDailyBonus(res.data);
    } catch (e) {}
  };

  const fetchAchievements = async () => {
    try {
      const res = await api.get('/achievements');
      if (res.data.success) setAchievements(res.data.achievements);
    } catch (e) {}
  };

  const claimRaceback = async () => {
    if (isDemo) {
      toast.error('Кешбэк недоступен в демо-режиме');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/bonus/raceback/claim');
      if (res.data.success) {
        updateBalance(res.data.balance);
        setCashbackData(prev => ({ ...prev, raceback: 0 }));
        toast.success(`Получено ${res.data.claimed?.toFixed(2)}₽`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const claimDailyBonus = async () => {
    if (isDemo) {
      toast.error('Ежедневный бонус недоступен в демо-режиме');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/bonus/daily/claim');
      if (res.data.success) {
        updateBalance(res.data.balance);
        toast.success(`🎁 ${res.data.message}`);
        fetchDailyBonus();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const activatePromo = async () => {
    if (!promoCode) return;
    if (isDemo) {
      toast.error('Промокоды недоступны в демо-режиме');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/promo/activate', { code: promoCode });
      if (res.data.success) {
        updateBalance(res.data.balance);
        toast.success(`Промокод активирован! +${res.data.reward?.toFixed(2)}₽`);
        setPromoCode('');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Промокод недействителен');
    }
    setLoading(false);
  };

  const claimAchievement = async (id) => {
    if (isDemo) {
      toast.error('Достижения недоступны в демо-режиме');
      return;
    }
    try {
      const res = await api.post(`/achievements/${id}/claim`);
      if (res.data.success) {
        updateBalance(res.data.balance);
        toast.success(`🏆 ${res.data.achievement}! +${res.data.reward}₽`);
        fetchAchievements();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
  };

  return (
    <div className="page bonus-page" data-testid="bonus-page">
      <h2><i className="fa-solid fa-gift"></i> Бонусы и достижения</h2>

      {isDemo && (
        <div className="demo-warning" data-testid="demo-warning-bonus">
          <i className="fa-solid fa-exclamation-triangle"></i>
          <div>
            <strong>Демо-режим</strong>
            <p>Бонусы и достижения недоступны. Авторизуйтесь через Telegram для получения наград!</p>
            <button className="btn-telegram" onClick={() => navigate('/login')}>
              <i className="fa-brands fa-telegram"></i> Войти через Telegram
            </button>
          </div>
        </div>
      )}

      <div className="bonus-tabs">
        <button className={activeTab === 'bonuses' ? 'active' : ''} onClick={() => setActiveTab('bonuses')}>
          <i className="fa-solid fa-gift"></i> Бонусы
        </button>
        <button className={activeTab === 'daily' ? 'active' : ''} onClick={() => setActiveTab('daily')}>
          <i className="fa-solid fa-calendar-day"></i> Ежедневный
        </button>
        <button className={activeTab === 'cashback' ? 'active' : ''} onClick={() => setActiveTab('cashback')}>
          <i className="fa-solid fa-percent"></i> Кешбэк
        </button>
        <button className={activeTab === 'tasks' ? 'active' : ''} onClick={() => setActiveTab('tasks')}>
          <i className="fa-solid fa-list-check"></i> Задания
        </button>
        <button className={activeTab === 'achievements' ? 'active' : ''} onClick={() => setActiveTab('achievements')}>
          <i className="fa-solid fa-trophy"></i> Достижения
        </button>
      </div>

      {activeTab === 'bonuses' && (
        <div className="bonus-cards">
          <div className="bonus-card raceback" data-testid="raceback-card">
            <div className="bonus-icon"><i className="fa-solid fa-rotate-left"></i></div>
            <h3>Кешбэк {cashbackData.level?.percent || 5}%</h3>
            <p>Уровень: {cashbackData.level?.name || 'Бронза'}</p>
            <div className="bonus-amount">{cashbackData.raceback?.toFixed(2)} ₽</div>
            <button onClick={claimRaceback} disabled={loading || cashbackData.raceback < 1 || user?.balance > 0 || isDemo} data-testid="claim-raceback-btn">
              {isDemo ? 'Недоступно в демо' : user?.balance > 0 ? 'Доступно при 0 балансе' : 'Забрать'}
            </button>
          </div>

          <div className="bonus-card promo" data-testid="promo-card">
            <div className="bonus-icon"><i className="fa-solid fa-ticket"></i></div>
            <h3>Промокод</h3>
            <p>Введите промокод для получения бонуса</p>
            <input type="text" value={promoCode} onChange={e => setPromoCode(e.target.value)} placeholder="Введите промокод" data-testid="promo-input" disabled={isDemo} />
            <button onClick={activatePromo} disabled={loading || !promoCode || isDemo} data-testid="activate-promo-btn">
              {isDemo ? 'Недоступно в демо' : 'Активировать'}
            </button>
          </div>

          <div className="bonus-card telegram" data-testid="telegram-card">
            <div className="bonus-icon"><i className="fa-brands fa-telegram"></i></div>
            <h3>Telegram канал</h3>
            <p>Подпишитесь на наш канал для получения эксклюзивных промокодов</p>
            <a href="https://t.me/easymoneycaspro" target="_blank" rel="noopener noreferrer" className="btn-telegram">
              Подписаться
            </a>
          </div>
        </div>
      )}

      {activeTab === 'daily' && (
        <div className="daily-bonus-section" data-testid="daily-bonus-section">
          <div className="daily-bonus-header">
            <h3><i className="fa-solid fa-calendar-star"></i> Ежедневный бонус</h3>
            <p>Заходите каждый день и получайте бонусы! Серия: {dailyBonus?.streak || 0} дней</p>
          </div>
          
          <div className="daily-bonus-days">
            {[1,2,3,4,5,6,7].map(day => {
              const defaultRewards = {1: 2, 2: 4, 3: 6, 4: 10, 5: 15, 6: 20, 7: 35};
              const currentDay = dailyBonus?.next_day || 1;
              const isPast = day < currentDay;
              const isCurrent = day === currentDay && dailyBonus?.can_claim;
              const isLocked = day > currentDay || (day === currentDay && !dailyBonus?.can_claim);
              const reward = dailyBonus?.rewards?.[day] || defaultRewards[day];
              
              return (
                <div key={day} className={`daily-day ${isPast ? 'claimed' : ''} ${isCurrent ? 'current' : ''} ${isLocked ? 'locked' : ''}`}>
                  <div className="day-number">День {day}</div>
                  <div className="day-reward">
                    {day === 7 ? <i className="fa-solid fa-crown"></i> : <i className="fa-solid fa-coins"></i>}
                    {reward}₽
                  </div>
                  {isPast && <i className="fa-solid fa-check-circle day-check"></i>}
                  {isLocked && day !== currentDay && <i className="fa-solid fa-lock day-lock"></i>}
                </div>
              );
            })}
          </div>
          
          <button 
            className="claim-daily-btn" 
            onClick={claimDailyBonus} 
            disabled={loading || !dailyBonus?.can_claim || isDemo}
            data-testid="claim-daily-btn"
          >
            {isDemo ? (
              <>Недоступно в демо</>
            ) : dailyBonus?.can_claim ? (
              <><i className="fa-solid fa-gift"></i> Получить {dailyBonus?.next_bonus}₽</>
            ) : (
              <><i className="fa-solid fa-clock"></i> Приходите завтра</>
            )}
          </button>
        </div>
      )}

      {activeTab === 'cashback' && (
        <div className="cashback-section" data-testid="cashback-section">
          {/* Current Level Card */}
          <div className="cashback-level-card">
            <div className="cashback-badge">
              <span className="cashback-icon">
                {cashbackData.level?.percent === 5 && '🥉'}
                {cashbackData.level?.percent === 10 && '🥈'}
                {cashbackData.level?.percent === 15 && '🥇'}
                {cashbackData.level?.percent === 20 && '💎'}
                {cashbackData.level?.percent === 25 && '💠'}
                {cashbackData.level?.percent === 30 && '👑'}
              </span>
              <span className="cashback-level-name">{cashbackData.level?.name || 'Бронза'}</span>
            </div>
            <div className="cashback-percent">{cashbackData.level?.percent || 5}%</div>
            <p className="cashback-desc">кешбэк от проигранных ставок</p>
            
            <div className="cashback-deposited">
              <span>Всего депозитов:</span>
              <strong>{(cashbackData.total_deposited || 0).toLocaleString('ru-RU')} ₽</strong>
            </div>
            
            {cashbackData.next_level && (
              <div className="cashback-progress">
                <div className="progress-info">
                  <span>До уровня "{cashbackData.next_level.name}"</span>
                  <span>{(cashbackData.total_deposited || 0).toLocaleString('ru-RU')} / {cashbackData.next_level.min_deposit.toLocaleString('ru-RU')} ₽</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ 
                      width: `${Math.min(100, ((cashbackData.total_deposited || 0) / cashbackData.next_level.min_deposit) * 100)}%` 
                    }}
                  ></div>
                </div>
              </div>
            )}
            
            {!cashbackData.next_level && cashbackData.total_deposited >= 200000 && (
              <div className="max-cashback-badge">
                <i className="fa-solid fa-crown"></i> Максимальный уровень!
              </div>
            )}
          </div>

          {/* Available Cashback */}
          <div className="cashback-available-card">
            <h3><i className="fa-solid fa-wallet"></i> Доступный кешбэк</h3>
            <div className="cashback-amount">{cashbackData.raceback?.toFixed(2) || '0.00'} ₽</div>
            <button 
              className="claim-cashback-btn" 
              onClick={claimRaceback} 
              disabled={loading || cashbackData.raceback < 1 || user?.balance > 0 || isDemo}
            >
              {isDemo ? 'Недоступно в демо' : user?.balance > 0 ? 'Доступно при 0₽ балансе' : 
               loading ? <i className="fa-solid fa-spinner fa-spin"></i> : 'Забрать кешбэк'}
            </button>
            <p className="cashback-note">Кешбэк можно забрать только при нулевом балансе</p>
          </div>

          {/* Levels Overview */}
          <div className="cashback-levels-overview">
            <h3>Уровни кешбэка</h3>
            <p className="levels-desc">Чем больше депозитов - тем выше процент кешбэка!</p>
            <div className="cashback-levels-grid">
              {(cashbackData.levels?.length > 0 ? cashbackData.levels : [
                {min_deposit: 0, percent: 5, name: "Бронза"},
                {min_deposit: 5000, percent: 10, name: "Серебро"},
                {min_deposit: 20000, percent: 15, name: "Золото"},
                {min_deposit: 50000, percent: 20, name: "Платина"},
                {min_deposit: 100000, percent: 25, name: "Бриллиант"},
                {min_deposit: 200000, percent: 30, name: "Легенда"}
              ]).map((level, i) => (
                <div 
                  key={i} 
                  className={`cashback-level-item ${cashbackData.level?.percent === level.percent ? 'active' : ''} ${(cashbackData.total_deposited || 0) >= level.min_deposit && cashbackData.level?.percent !== level.percent ? 'completed' : ''}`}
                >
                  <div className="level-emoji">
                    {level.percent === 5 && '🥉'}
                    {level.percent === 10 && '🥈'}
                    {level.percent === 15 && '🥇'}
                    {level.percent === 20 && '💎'}
                    {level.percent === 25 && '💠'}
                    {level.percent === 30 && '👑'}
                  </div>
                  <div className="level-name">{level.name}</div>
                  <div className="level-percent-value">{level.percent}%</div>
                  <div className="level-requirement">
                    {level.min_deposit === 0 ? 'Старт' : `${(level.min_deposit / 1000).toFixed(0)}K₽+`}
                  </div>
                  {cashbackData.level?.percent === level.percent && (
                    <i className="fa-solid fa-check-circle level-active-check"></i>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="daily-tasks-section" data-testid="daily-tasks-section">
          <div className="tasks-header">
            <h3><i className="fa-solid fa-list-check"></i> Ежедневные задания</h3>
            <p>Выполняйте задания и получайте награды! Задания обновляются каждый день.</p>
          </div>
          
          {isDemo ? (
            <div className="demo-warning">
              <i className="fa-solid fa-exclamation-triangle"></i>
              <span>Задания недоступны в демо-режиме. Авторизуйтесь через Telegram.</span>
            </div>
          ) : (
            <div className="tasks-list">
              {dailyTasks.map(task => (
                <div key={task.id} className={`task-card ${task.completed ? 'completed' : ''} ${task.claimed ? 'claimed' : ''}`} data-testid={`task-${task.id}`}>
                  <div className="task-icon">
                    <i className={`fa-solid ${task.icon}`}></i>
                  </div>
                  <div className="task-info">
                    <h4>{task.name}</h4>
                    <p>{task.desc}</p>
                    <div className="task-progress">
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${Math.min(100, (task.current / task.target) * 100)}%` }}></div>
                      </div>
                      <span className="progress-text">{task.current}/{task.target}</span>
                    </div>
                  </div>
                  <div className="task-reward">
                    <span className="reward-amount">+{task.reward}₽</span>
                    {task.claimed ? (
                      <span className="task-claimed"><i className="fa-solid fa-check-circle"></i> Получено</span>
                    ) : task.completed ? (
                      <button className="claim-task-btn" onClick={() => claimDailyTask(task.id)} disabled={loading}>
                        <i className="fa-solid fa-gift"></i> Забрать
                      </button>
                    ) : (
                      <span className="task-pending"><i className="fa-solid fa-hourglass-half"></i> В процессе</span>
                    )}
                  </div>
                </div>
              ))}
              {dailyTasks.length === 0 && (
                <div className="no-tasks">Загрузка заданий...</div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'achievements' && (
        <div className="achievements-section" data-testid="achievements-section">
          <div className="achievements-grid">
            {achievements.map(a => (
              <div key={a.id} className={`achievement-card ${a.unlocked ? 'unlocked' : 'locked'}`} data-testid={`achievement-${a.id}`}>
                <div className="achievement-icon">
                  <i className={`fa-solid ${a.icon}`}></i>
                </div>
                <div className="achievement-info">
                  <h4>{a.name}</h4>
                  <p>{a.desc}</p>
                  <div className="achievement-reward">+{a.reward}₽</div>
                </div>
                {a.unlocked && (
                  <button className="claim-achievement-btn" onClick={() => claimAchievement(a.id)} disabled={isDemo}>
                    <i className="fa-solid fa-check"></i>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const Referral = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [referrals, setReferrals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showReferrals, setShowReferrals] = useState(false);

  const isDemo = user?.is_demo;

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await api.get('/ref/stats');
      if (res.data.success) setStats(res.data);
    } catch (e) {}
  };

  const fetchReferrals = async () => {
    try {
      const res = await api.get('/ref/list');
      if (res.data.success) setReferrals(res.data.referrals || []);
    } catch (e) {
      toast.error('Ошибка загрузки списка рефералов');
    }
  };

  const toggleReferrals = () => {
    if (!showReferrals) {
      fetchReferrals();
    }
    setShowReferrals(!showReferrals);
  };

  const withdrawRef = async () => {
    if (isDemo) {
      toast.error('Партнёрская программа недоступна в демо-режиме');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/ref/withdraw');
      if (res.data.success) {
        updateBalance(res.data.balance);
        fetchStats();
        toast.success(`Выведено ${res.data.withdrawn?.toFixed(2)}₽`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
    setLoading(false);
  };

  const copyLink = () => {
    if (isDemo) {
      toast.error('Авторизуйтесь через Telegram для получения реферальной ссылки');
      return;
    }
    navigator.clipboard.writeText(`${window.location.origin}/?ref=${stats?.ref_link}`);
    toast.success('Ссылка скопирована!');
  };

  // Block demo users with message
  // Demo users can view stats but not withdraw
  const currentLevel = stats?.level || { name: "Новичок", percent: 10, min_refs: 0 };
  const nextLevel = stats?.next_level;
  const depositedRefs = stats?.deposited_refs || 0;
  const progressToNext = nextLevel ? ((depositedRefs - currentLevel.min_refs) / (nextLevel.min_refs - currentLevel.min_refs)) * 100 : 100;

  return (
    <div className="page ref-page" data-testid="ref-page">
      <h2><i className="fa-solid fa-users"></i> Партнёрская программа</h2>
      
      {isDemo && (
        <div className="demo-warning-small" data-testid="demo-warning-ref">
          <i className="fa-solid fa-info-circle"></i>
          <span>Для вывода бонусов авторизуйтесь через Telegram</span>
          <button className="btn-telegram-small" onClick={() => navigate('/login')}>
            <i className="fa-brands fa-telegram"></i> Войти
          </button>
        </div>
      )}
      
      {/* Current Level Card */}
      <div className="ref-level-card" data-testid="ref-level-card">
        <div className="level-badge">
          <span className="level-icon">
            {currentLevel.percent === 10 && '🌱'}
            {currentLevel.percent === 20 && '⭐'}
            {currentLevel.percent === 30 && '🔥'}
            {currentLevel.percent === 40 && '👑'}
          </span>
          <span className="level-name">{currentLevel.name}</span>
        </div>
        <div className="level-percent">{currentLevel.percent}%</div>
        <p className="level-desc">от депозитов рефералов</p>
        
        {nextLevel && (
          <div className="level-progress">
            <div className="progress-info">
              <span>До уровня "{nextLevel.name}"</span>
              <span>{depositedRefs}/{nextLevel.min_refs} рефералов</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${Math.min(100, progressToNext)}%` }}></div>
            </div>
          </div>
        )}
        
        {!nextLevel && (
          <div className="max-level-badge">
            <i className="fa-solid fa-crown"></i> Максимальный уровень!
          </div>
        )}
      </div>

      {/* Levels Overview */}
      <div className="ref-levels-overview">
        <h3>Уровни партнёрской программы</h3>
        <div className="levels-grid">
          {(stats?.levels || [
            {min_refs: 0, percent: 10, name: "Новичок"},
            {min_refs: 10, percent: 20, name: "Партнёр"},
            {min_refs: 25, percent: 30, name: "Мастер"},
            {min_refs: 50, percent: 40, name: "Легенда"}
          ]).map((level, i) => (
            <div key={i} className={`level-card ${currentLevel.percent === level.percent ? 'active' : ''} ${currentLevel.percent > level.percent ? 'completed' : ''}`}>
              <div className="level-emoji">
                {level.percent === 10 && '🌱'}
                {level.percent === 20 && '⭐'}
                {level.percent === 30 && '🔥'}
                {level.percent === 40 && '👑'}
              </div>
              <div className="level-name">{level.name}</div>
              <div className="level-percent-small">{level.percent}%</div>
              <div className="level-req">{level.min_refs === 0 ? 'Старт' : `${level.min_refs}+ депов`}</div>
              {currentLevel.percent === level.percent && <i className="fa-solid fa-check-circle level-check"></i>}
            </div>
          ))}
        </div>
      </div>

      <div className="ref-link-box" data-testid="ref-link-box">
        <label>Ваша реферальная ссылка:</label>
        <div className="ref-link">
          <input type="text" value={`${window.location.origin}/?ref=${stats?.ref_link || ''}`} readOnly />
          <button onClick={copyLink}><i className="fa-solid fa-copy"></i></button>
        </div>
      </div>

      <div className="ref-stats">
        <div className="ref-stat">
          <i className="fa-solid fa-user-plus"></i>
          <div className="stat-value">{stats?.referalov || 0}</div>
          <div className="stat-label">Всего рефералов</div>
        </div>
        <div className="ref-stat highlight">
          <i className="fa-solid fa-money-bill-transfer"></i>
          <div className="stat-value">{stats?.deposited_refs || 0}</div>
          <div className="stat-label">С депозитом</div>
        </div>
        <div className="ref-stat">
          <i className="fa-solid fa-coins"></i>
          <div className="stat-value">{stats?.income?.toFixed(2) || '0.00'} ₽</div>
          <div className="stat-label">Доступно</div>
        </div>
        <div className="ref-stat">
          <i className="fa-solid fa-chart-line"></i>
          <div className="stat-value">{stats?.income_all?.toFixed(2) || '0.00'} ₽</div>
          <div className="stat-label">Всего заработано</div>
        </div>
      </div>

      <button className="btn-withdraw-ref" onClick={withdrawRef} disabled={loading || (stats?.income || 0) < 150} data-testid="withdraw-ref-btn">
        {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : `Вывести ${stats?.income?.toFixed(2) || '0.00'} ₽`}
      </button>
      <p className="ref-note">Минимум для вывода: 150₽. Требуется депозит в текущем месяце.</p>

      {/* Referrals List */}
      <div className="ref-list-section">
        <button className="btn-show-refs" onClick={toggleReferrals} data-testid="show-refs-btn">
          <i className={`fa-solid fa-chevron-${showReferrals ? 'up' : 'down'}`}></i>
          {showReferrals ? 'Скрыть рефералов' : `Показать рефералов (${stats?.referalov || 0})`}
        </button>
        
        {showReferrals && (
          <div className="ref-list" data-testid="ref-list">
            {referrals.length === 0 ? (
              <p className="no-refs">У вас пока нет рефералов. Поделитесь ссылкой!</p>
            ) : (
              <table className="ref-table">
                <thead>
                  <tr>
                    <th>Пользователь</th>
                    <th>Дата регистрации</th>
                    <th>Депозиты</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {referrals.map((ref, i) => (
                    <tr key={i} className={ref.has_deposited ? 'deposited' : ''}>
                      <td>{ref.name || ref.username || `Реферал ${i + 1}`}</td>
                      <td>{ref.registered ? new Date(ref.registered).toLocaleDateString('ru-RU') : '-'}</td>
                      <td>{ref.total_deposited?.toFixed(2) || '0.00'} ₽</td>
                      <td>
                        <span className={`ref-status ${ref.has_deposited ? 'active' : 'pending'}`}>
                          {ref.has_deposited ? '✓ Активный' : '⏳ Без депозита'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};


// Crash Game - Online mode with history
const CrashGame = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [bet, setBet] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [currentMult, setCurrentMult] = useState(1.0);
  const [crashed, setCrashed] = useState(false);
  const [gamePhase, setGamePhase] = useState('waiting');
  const [betId, setBetId] = useState(null);
  const [history, setHistory] = useState([]);
  const [countdown, setCountdown] = useState(3);
  const [cashedOut, setCashedOut] = useState(false);
  const [serverCrashPoint, setServerCrashPoint] = useState(null);
  
  // Critical refs for synchronization
  const gameLoopRef = useRef(null);
  const animationRef = useRef(null);
  const isGameRunningRef = useRef(false);
  const serverCrashPointRef = useRef(null);  // Ref for animation to access
  const betIdRef = useRef(null);  // Ref for animation to access
  const cashedOutRef = useRef(false);  // Ref for animation to access
  const displayCrashPointRef = useRef(null);  // Crash point for display (when no bet)

  // Keep refs in sync with state
  useEffect(() => {
    serverCrashPointRef.current = serverCrashPoint;
  }, [serverCrashPoint]);
  
  useEffect(() => {
    betIdRef.current = betId;
  }, [betId]);
  
  useEffect(() => {
    cashedOutRef.current = cashedOut;
  }, [cashedOut]);

  // Fetch real history from DB
  const fetchHistory = async () => {
    try {
      const res = await api.get('/games/crash/history');
      if (res.data.success && res.data.history) {
        setHistory(res.data.history.slice(0, 20));
      }
    } catch (e) {
      console.error('Failed to load history:', e);
    }
  };

  // Load history on mount and refresh every 10 seconds
  useEffect(() => {
    fetchHistory();
    const historyInterval = setInterval(fetchHistory, 10000);
    return () => clearInterval(historyInterval);
  }, []);

  // Start game loop ONCE
  useEffect(() => {
    if (!isGameRunningRef.current) {
      isGameRunningRef.current = true;
      startGameLoop();
    }
    
    // Cleanup on unmount
    return () => {
      isGameRunningRef.current = false;
      if (gameLoopRef.current) clearTimeout(gameLoopRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  const startGameLoop = () => {
    if (!isGameRunningRef.current) return;
    
    // Phase 1: Waiting
    setGamePhase('waiting');
    setCountdown(3);
    setCrashed(false);
    setCurrentMult(1.0);
    setResult(null);
    setBetId(null);
    setCashedOut(false);
    setServerCrashPoint(null);
    
    // Reset refs
    serverCrashPointRef.current = null;
    betIdRef.current = null;
    cashedOutRef.current = false;
    displayCrashPointRef.current = null;
    
    let time = 3;
    const waitInterval = setInterval(() => {
      time--;
      setCountdown(time);
      if (time <= 0) {
        clearInterval(waitInterval);
        startBettingPhase();
      }
    }, 1000);
    
    gameLoopRef.current = waitInterval;
  };

  const startBettingPhase = () => {
    if (!isGameRunningRef.current) return;
    
    setGamePhase('betting');
    setCountdown(5);
    
    let time = 5;
    const bettingInterval = setInterval(() => {
      time--;
      setCountdown(time);
      if (time <= 0) {
        clearInterval(bettingInterval);
        startFlightPhase();
      }
    }, 1000);
    
    gameLoopRef.current = bettingInterval;
  };

  const startFlightPhase = () => {
    if (!isGameRunningRef.current) return;
    
    setGamePhase('flying');
    setCrashed(false);
    
    // Generate display crash point for when player has no bet
    // This is only used for visual display when user is watching, not playing
    // SECURITY: When player has a bet, they don't know the real crash point
    const r = Math.random();
    let displayCrash;
    if (r < 0.99) {
      displayCrash = 0.99 / (1 - r);
    } else {
      displayCrash = Math.random() * 900 + 100;
    }
    displayCrash = Math.min(displayCrash, 1000);
    displayCrash = parseFloat(displayCrash.toFixed(2));
    displayCrashPointRef.current = displayCrash;
    
    let startTime = Date.now();
    let hasProcessedResult = false;
    let lastStatusCheck = 0;
    
    const checkCrashStatus = async () => {
      if (!betIdRef.current || cashedOutRef.current || hasProcessedResult) return null;
      
      try {
        const res = await api.get(`/games/crash/status/${betIdRef.current}?current_mult=${currentMultiplier}`);
        return res.data;
      } catch (e) {
        console.error('Status check failed:', e);
        return null;
      }
    };
    
    let currentMultiplier = 1.0;
    
    const animate = async () => {
      if (!isGameRunningRef.current) {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
          animationRef.current = null;
        }
        return;
      }
      
      // CONSTANT LINEAR SPEED - multiplier increases by 0.15 per second
      const elapsed = (Date.now() - startTime) / 1000;
      const mult = 1.0 + (elapsed * 0.15);
      const newMult = parseFloat(mult.toFixed(2));
      currentMultiplier = newMult;  // Update for status check
      
      // Check crash status from server every 200ms when player has a bet
      const now = Date.now();
      if (betIdRef.current && !cashedOutRef.current && !hasProcessedResult && now - lastStatusCheck > 200) {
        lastStatusCheck = now;
        const status = await checkCrashStatus();
        if (status && status.crash_point) {
          // Got crash point from server - check if we crashed
          if (newMult >= status.crash_point || status.status === 'lose') {
            // Server says we crashed!
            hasProcessedResult = true;
            setCurrentMult(status.crash_point);
            setCrashed(true);
            setGamePhase('crashed');
            
            toast.error(`💥 Краш на x${status.crash_point}!`);
            setResult({
              status: 'crashed',
              crashPoint: status.crash_point,
              win: 0
            });
            
            // Refresh balance
            try {
              const meRes = await api.get('/auth/me');
              if (meRes.data.success) {
                updateBalance(meRes.data.user.balance);
              }
            } catch (e) {}
            
            if (animationRef.current) {
              cancelAnimationFrame(animationRef.current);
              animationRef.current = null;
            }
            
            setTimeout(() => fetchHistory(), 500);
            
            gameLoopRef.current = setTimeout(() => {
              if (isGameRunningRef.current) {
                startGameLoop();
              }
            }, 4000);
            return;
          }
        }
      }
      
      // For display mode (no bet), use displayCrashPoint
      const activeCrashPoint = !betIdRef.current ? displayCrashPointRef.current : null;
      
      // Check if crashed - only for display mode (no bet)
      if (!betIdRef.current && activeCrashPoint && newMult >= activeCrashPoint) {
        // Display crash for spectators
        setCurrentMult(activeCrashPoint);
        setCrashed(true);
        setGamePhase('crashed');
        
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
          animationRef.current = null;
        }
        
        setTimeout(() => fetchHistory(), 500);
        
        gameLoopRef.current = setTimeout(() => {
          if (isGameRunningRef.current) {
            startGameLoop();
          }
        }, 4000);
      } else if (newMult >= 1000) {
        // Max multiplier reached
        setCurrentMult(1000);
        setCrashed(true);
        setGamePhase('crashed');
        
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
          animationRef.current = null;
        }
        
        gameLoopRef.current = setTimeout(() => {
          if (isGameRunningRef.current) {
            startGameLoop();
          }
        }, 4000);
      } else {
        setCurrentMult(newMult);
        animationRef.current = requestAnimationFrame(animate);
      }
    };
    
    animationRef.current = requestAnimationFrame(animate);
  };
  
  // Fetch crash result from server (called when max mult reached or periodically)
  const fetchCrashResult = async (currentBetId, finalMult) => {
    if (!currentBetId) return;
    try {
      const res = await api.post(`/games/crash/result/${currentBetId}`, { final_multiplier: finalMult });
      if (res.data.status === 'crashed') {
        toast.error(`💥 Краш на x${res.data.crash_point}!`);
        setResult({
          status: 'crashed',
          crashPoint: res.data.crash_point,
          win: 0
        });
      }
      // Refresh balance
      const meRes = await api.get('/auth/me');
      if (meRes.data.success) {
        updateBalance(meRes.data.user.balance);
      }
    } catch (e) {
      console.error('Failed to fetch crash result:', e);
    }
  };

  const placeBet = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    if (gamePhase !== 'betting') return toast.error('Дождитесь следующего раунда');
    
    setLoading(true);
    setCashedOut(false);
    cashedOutRef.current = false;
    
    try {
      const res = await api.post('/games/crash/bet', { bet });
      if (res.data.success) {
        // Update state - NOTE: crash_point is NOT sent by server for security
        setBetId(res.data.bet_id);
        betIdRef.current = res.data.bet_id;
        
        // Обновляем баланс (списана ставка)
        updateBalance(res.data.balance);
        
        // Запрашиваем актуальный баланс
        try {
          const meRes = await api.get('/auth/me');
          if (meRes.data.success) {
            updateBalance(meRes.data.user.balance);
          }
        } catch (e) {
          console.error('Failed to refresh user:', e);
        }
        
        toast.success('Ставка принята! Нажмите "Забрать" во время полёта');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  const cashout = async () => {
    if (!betId || cashedOut || crashed) return;
    
    // Сохраняем текущий множитель ДО отправки запроса
    const cashoutMultiplier = currentMult;
    setCashedOut(true);
    cashedOutRef.current = true;
    
    try {
      const res = await api.post(`/games/crash/cashout/${betId}`, { 
        multiplier: cashoutMultiplier 
      });
      
      if (res.data.success) {
        // Обновляем баланс
        updateBalance(res.data.balance);
        
        // Запрашиваем актуальный баланс
        try {
          const meRes = await api.get('/auth/me');
          if (meRes.data.success) {
            updateBalance(meRes.data.user.balance);
          }
        } catch (e) {
          console.error('Failed to refresh user:', e);
        }
        
        setResult({
          status: 'cashed_out',
          multiplier: res.data.multiplier,
          win: res.data.win
        });
        
        toast.success(`💰 Выигрыш: +${res.data.win.toFixed(2)}₽ (x${res.data.multiplier})`);
      } else {
        // Сервер вернул success: false - значит краш
        toast.error(res.data.message || 'Слишком поздно! Краш!');
        setCashedOut(false);
        setCrashed(true);
        setGamePhase('crashed');
      }
    } catch (e) {
      const errorDetail = e.response?.data?.detail || 'Ошибка';
      toast.error(errorDetail);
      // Если ставка уже завершена или краш - отмечаем это
      if (errorDetail.includes('завершена') || errorDetail.includes('Краш')) {
        setCrashed(true);
        setGamePhase('crashed');
      }
      setCashedOut(false);
    }
  };

  const checkResult = async (finalMult) => {
    if (!betId) return;
    
    try {
      const res = await api.post(`/games/crash/result/${betId}`, { final_multiplier: finalMult });
      if (res.data.success) {
        // ✅ Обновляем баланс из результата
        updateBalance(res.data.balance);
        
        // ✅ ДОПОЛНИТЕЛЬНО: Запрашиваем актуального пользователя для точности
        try {
          const meRes = await api.get('/auth/me');
          if (meRes.data.success) {
            updateBalance(meRes.data.user.balance);
          }
        } catch (e) {
          console.error('Failed to refresh user:', e);
        }
        
        // Показываем результат
        setResult({
          status: res.data.status,
          crashPoint: res.data.crash_point,
          win: res.data.win
        });
        
        if (res.data.status === 'win') {
          toast.success(`💰 Выигрыш: +${res.data.win.toFixed(2)}₽ (x${autoCashout})`);
        } else {
          toast.error(`💥 Краш на x${res.data.crash_point}!`);
        }
      }
    } catch (e) {
      console.error('Failed to get result:', e);
    }
  };

  return (
    <div className="page game-page crash-page" data-testid="crash-page">
      <div className="crash-container-new">
        {/* History bar - REAL from DB */}
        <div className="crash-history-bar" data-testid="crash-history">
          <div className="history-label">
            <i className="fa-solid fa-clock-rotate-left"></i>
            <span>История раундов</span>
          </div>
          <div className="history-items">
            {history.map((h, i) => (
              <div key={`${h.multiplier}-${i}`} className={`history-multiplier ${h.multiplier < 2 ? 'red' : h.multiplier >= 10 ? 'gold' : 'green'}`}>
                {h.multiplier.toFixed(2)}x
              </div>
            ))}
          </div>
        </div>
        
        {/* Main game area */}
        <div className="crash-game-area">
          <div className="crash-display-card" data-testid="crash-board">
            {gamePhase === 'waiting' ? (
              <div className="crash-waiting-state">
                <div className="waiting-icon">
                  <i className="fa-solid fa-hourglass-half"></i>
                </div>
                <h2>Ожидание</h2>
                <div className="countdown-display">{countdown}</div>
                <p>Подготовка раунда</p>
              </div>
            ) : gamePhase === 'betting' ? (
              <div className="crash-waiting-state">
                <div className="waiting-icon">
                  <i className="fa-solid fa-hand-holding-dollar"></i>
                </div>
                <h2>Приём ставок</h2>
                <div className="countdown-display">{countdown}</div>
                <p>Успей поставить!</p>
              </div>
            ) : (
              <div className="crash-active-state">
                <div className={`multiplier-big ${crashed ? 'crashed' : 'flying'}`}>
                  {currentMult.toFixed(2)}x
                </div>
                <div className={`status-indicator ${crashed ? 'crashed' : 'flying'}`}>
                  {crashed ? (
                    <>
                      <i className="fa-solid fa-bomb"></i>
                      <span>КРАШ!</span>
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-rocket"></i>
                      <span>Летим...</span>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Controls */}
          <div className="crash-controls-card">
            <div className="control-row">
              <div className="control-group">
                <label><i className="fa-solid fa-coins"></i> Ставка</label>
                <div className="bet-input-wrapper">
                  <button onClick={() => setBet(Math.max(1, bet / 2))} disabled={gamePhase !== 'betting'} className="bet-modifier">½</button>
                  <input 
                    type="number" 
                    value={bet} 
                    onChange={(e) => setBet(Math.max(1, parseFloat(e.target.value) || 1))} 
                    disabled={gamePhase !== 'betting'}
                    className="bet-input"
                  />
                  <span className="currency">₽</span>
                  <button onClick={() => setBet(Math.min(user?.balance || 10000, bet * 2))} disabled={gamePhase !== 'betting'} className="bet-modifier">×2</button>
                </div>
              </div>
            </div>
            
            {result && (
              <div className={`game-result ${result.status}`}>
                <i className={`fa-solid ${result.status === 'cashed_out' ? 'fa-trophy' : 'fa-xmark'}`}></i>
                <span>
                  {result.status === 'cashed_out' 
                    ? `Выигрыш ${result.win.toFixed(2)}₽ (x${result.multiplier})` 
                    : `Краш! Вы проиграли ${bet}₽`}
                </span>
              </div>
            )}
            
            {gamePhase === 'betting' && !betId ? (
              <button className="play-button" onClick={placeBet} disabled={loading || !user} data-testid="crash-play-btn">
                {loading ? (
                  <><i className="fa-solid fa-spinner fa-spin"></i> Обработка...</>
                ) : (
                  <>
                    <i className="fa-solid fa-play"></i>
                    Поставить {bet}₽
                  </>
                )}
              </button>
            ) : gamePhase === 'flying' && betId && !cashedOut && !crashed ? (
              <button className="play-button cashout-button" onClick={cashout} data-testid="crash-cashout-btn">
                <i className="fa-solid fa-hand-holding-dollar"></i>
                Забрать {(bet * currentMult).toFixed(2)}₽
              </button>
            ) : (
              <button className="play-button waiting" disabled data-testid="crash-play-btn">
                {gamePhase === 'waiting' ? (
                  <><i className="fa-solid fa-clock"></i> Ожидание...</>
                ) : gamePhase === 'crashed' ? (
                  <><i className="fa-solid fa-hourglass"></i> Следующий раунд...</>
                ) : cashedOut ? (
                  <><i className="fa-solid fa-check-circle"></i> Выведено!</>
                ) : betId && gamePhase === 'betting' ? (
                  <><i className="fa-solid fa-check-circle"></i> Ставка принята</>
                ) : (
                  <><i className="fa-solid fa-rocket"></i> Игра идёт...</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const X100Game = () => {
  const { user, updateBalance } = useAuth();
  const navigate = useNavigate();
  const [bet, setBet] = useState(10);
  const [selectedCoef, setSelectedCoef] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [spinning, setSpinning] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [spinCount, setSpinCount] = useState(0);

  const coefficients = [2, 3, 10, 15, 20, 100];
  const colors = { 
    2: '#4ade80',   // Green
    3: '#60a5fa',   // Blue  
    10: '#f472b6',  // Pink
    15: '#fbbf24',  // Yellow/Gold
    20: '#a78bfa',  // Purple
    100: '#ef4444'  // Red (Jackpot)
  };

  // Exact wheel positions matching backend X100_WHEEL
  const wheelData = [
    2, 3, 2, 15, 2, 3, 2, 20, 2, 15, 2, 3, 2, 3, 2, 15, 2, 3, 10, 3, 2, 10, 2, 3, 2,
    100, // Position 25 - Jackpot
    2, 3, 2, 10, 2, 3, 2, 3, 2, 15, 2, 3, 2, 3, 2, 20, 2, 3, 2, 10, 2, 3, 2, 10,
    2, 3, 2, 15, 2, 3, 2, 3, 2, 10, 20, 3, 2, 3, 2, 15, 2, 10, 2, 3, 2, 20, 2, 3, 2,
    15, 2, 3, 2, 10, 2, 3, 2, 3, 2, 10, 2, 3, 2, 3, 2, 10, 2, 3, 2, 3, 2, 3, 2
  ];

  const totalSegments = wheelData.length;
  const segmentAngle = 360 / totalSegments;

  const play = async () => {
    if (!user) return navigate('/login');
    if (user.balance < bet) return toast.error('Недостаточно средств');
    
    setLoading(true);
    setSpinning(true);
    setResult(null);
    
    try {
      const res = await api.post('/games/x100/play', { bet, coef: selectedCoef });
      
      if (res.data.success) {
        const position = res.data.position;
        
        // Calculate the exact rotation needed
        // Pointer is at TOP (12 o'clock position)
        // Segment 0 starts at TOP and goes clockwise
        // To land on segment N, we rotate the wheel so segment N is at TOP
        // Rotation is clockwise, so we need: -(position * segmentAngle) - segmentAngle/2
        // The -segmentAngle/2 centers the pointer in the middle of the segment
        
        const fullRotations = 360 * (5 + spinCount); // Multiple full rotations for effect
        const targetAngle = position * segmentAngle + segmentAngle / 2;
        const finalRotation = fullRotations + (360 - targetAngle);
        
        setRotation(finalRotation);
        setSpinCount(prev => prev + 1);
        
        setTimeout(() => {
          setSpinning(false);
          setResult(res.data);
          updateBalance(res.data.balance);
          
          if (res.data.status === 'win') {
            toast.success(`🎉 Победа! +${res.data.win?.toFixed(2)}₽ (x${res.data.result_coef})`);
          } else {
            toast.error(`Выпало x${res.data.result_coef}. Вы выбрали x${selectedCoef}`);
          }
          setLoading(false);
        }, 4000);
      }
    } catch (e) {
      setSpinning(false);
      toast.error(e.response?.data?.detail || 'Ошибка');
      setLoading(false);
    }
  };

  return (
    <div className="page game-page x100-page" data-testid="x100-page">
      <div className="game-container">
        <div className="game-board x100-board" data-testid="x100-board">
          <div className="x100-wheel-container">
            {/* SVG Wheel - segments start from top (12 o'clock) and go clockwise */}
            <svg 
              viewBox="0 0 200 200" 
              className="x100-wheel-svg"
              style={{ 
                transform: `rotate(${rotation}deg)`,
                transition: spinning ? 'transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'none'
              }}
            >
              {wheelData.map((coef, i) => {
                // Each segment spans segmentAngle degrees
                // Start from -90 so first segment is at top (12 o'clock)
                const startAngle = (i * segmentAngle) - 90;
                const endAngle = ((i + 1) * segmentAngle) - 90;
                const startRad = startAngle * Math.PI / 180;
                const endRad = endAngle * Math.PI / 180;
                const x1 = 100 + 95 * Math.cos(startRad);
                const y1 = 100 + 95 * Math.sin(startRad);
                const x2 = 100 + 95 * Math.cos(endRad);
                const y2 = 100 + 95 * Math.sin(endRad);
                
                return (
                  <path
                    key={i}
                    d={`M 100 100 L ${x1} ${y1} A 95 95 0 0 1 ${x2} ${y2} Z`}
                    fill={colors[coef]}
                    stroke="#1a1a2e"
                    strokeWidth="0.5"
                  />
                );
              })}
              <circle cx="100" cy="100" r="35" fill="#1a1a2e" stroke="#fbbf24" strokeWidth="3"/>
            </svg>
            
            {/* Pointer at top */}
            <div className="x100-pointer"></div>
            
            {/* Center display */}
            <div className="x100-center">
              {result ? (
                <div className={`x100-result ${result.status}`}>
                  <div className="x100-result-coef" style={{ color: colors[result.result_coef] }}>x{result.result_coef}</div>
                  <div className="x100-result-win">{result.win > 0 ? `+${result.win?.toFixed(2)}₽` : '0₽'}</div>
                </div>
              ) : (
                <div className="x100-logo">x100</div>
              )}
            </div>
          </div>
        </div>
        
        <div className="game-controls" data-testid="x100-controls">
          <h2><i className="fa-solid fa-circle-notch"></i> X100</h2>
          
          <div className="control-group">
            <label>Выберите множитель</label>
            <div className="x100-coefs">
              {coefficients.map(c => (
                <button 
                  key={c} 
                  className={`x100-coef-btn ${selectedCoef === c ? 'active' : ''}`}
                  onClick={() => setSelectedCoef(c)}
                  style={{ 
                    backgroundColor: colors[c],
                    borderColor: selectedCoef === c ? '#fff' : 'transparent',
                    transform: selectedCoef === c ? 'scale(1.1)' : 'scale(1)'
                  }}
                  disabled={loading}
                >
                  x{c}
                </button>
              ))}
            </div>
          </div>
          
          <div className="control-group">
            <label>Ставка</label>
            <div className="bet-input">
              <button onClick={() => setBet(Math.max(1, bet / 2))} disabled={loading}>½</button>
              <input type="number" value={bet} onChange={e => setBet(Math.max(1, +e.target.value))} disabled={loading} data-testid="x100-bet-input" />
              <button onClick={() => setBet(Math.min(user?.balance || 1000, bet * 2))} disabled={loading}>×2</button>
            </div>
          </div>
          
          <div className="potential-win" style={{ 
            background: `linear-gradient(135deg, ${colors[selectedCoef]}20, transparent)`,
            borderLeft: `4px solid ${colors[selectedCoef]}`
          }}>
            При выигрыше x{selectedCoef}: <strong style={{ color: colors[selectedCoef] }}>{(bet * selectedCoef).toFixed(2)} ₽</strong>
          </div>
          
          <button className="btn-start" onClick={play} disabled={loading} data-testid="x100-play-btn">
            {loading ? (
              spinning ? <><i className="fa-solid fa-circle-notch fa-spin"></i> Крутится...</> : <i className="fa-solid fa-spinner fa-spin"></i>
            ) : <><i className="fa-solid fa-play"></i> Крутить</>}
          </button>
        </div>
      </div>
    </div>
  );
};

// Policy Page

// Support Chat Component
const SupportChat = () => {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user && open) {
      fetchMessages();
      const interval = setInterval(fetchMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [user, open]);

  const fetchMessages = async () => {
    try {
      const res = await api.get('/support/messages');
      if (res.data.success) setMessages(res.data.messages);
    } catch (e) {}
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    setLoading(true);
    try {
      await api.post('/support/message', { message: newMessage });
      setNewMessage('');
      fetchMessages();
    } catch (e) {
      toast.error('Ошибка отправки');
    }
    setLoading(false);
  };

  if (!user) return null;

  return (
    <>
      <button className="support-btn" onClick={() => setOpen(!open)} data-testid="support-btn">
        <i className="fa-solid fa-headset"></i>
      </button>
      {open && (
        <div className="support-chat" data-testid="support-chat">
          <div className="support-header">
            <h3><i className="fa-solid fa-headset"></i> Поддержка</h3>
            <button onClick={() => setOpen(false)}><i className="fa-solid fa-times"></i></button>
          </div>
          <div className="support-messages">
            {messages.length === 0 ? (
              <div className="no-messages">
                <i className="fa-solid fa-comments"></i>
                <p>Напишите нам, мы всегда на связи!</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`support-message ${msg.is_admin ? 'admin' : 'user'}`}>
                  <div className="msg-sender">{msg.is_admin ? 'Поддержка' : 'Вы'}</div>
                  <div className="msg-text">{msg.message}</div>
                  <div className="msg-time">{new Date(msg.created_at).toLocaleTimeString()}</div>
                </div>
              ))
            )}
          </div>
          <div className="support-input">
            <input 
              type="text" 
              value={newMessage} 
              onChange={e => setNewMessage(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && sendMessage()}
              placeholder="Введите сообщение..."
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !newMessage.trim()}>
              <i className="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

// Support Page - Full page support chat
const SupportPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    fetchMessages();
    const interval = setInterval(fetchMessages, 3000);
    return () => clearInterval(interval);
  }, [user, navigate]);

  const fetchMessages = async () => {
    try {
      const res = await api.get('/support/messages');
      if (res.data.success) setMessages(res.data.messages);
    } catch (e) {}
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    setLoading(true);
    try {
      await api.post('/support/message', { message: newMessage });
      setNewMessage('');
      fetchMessages();
      toast.success('Сообщение отправлено');
    } catch (e) {
      toast.error('Ошибка отправки');
    }
    setLoading(false);
  };

  return (
    <div className="page support-page" data-testid="support-page">
      <div className="support-page-container">
        <div className="support-page-header">
          <h2><i className="fa-solid fa-headset"></i> Служба поддержки</h2>
          <p>Напишите нам, и мы ответим в ближайшее время!</p>
        </div>
        
        <div className="support-page-chat">
          <div className="support-page-messages">
            {messages.length === 0 ? (
              <div className="no-messages-page">
                <i className="fa-solid fa-comments"></i>
                <h3>Начните диалог</h3>
                <p>Опишите вашу проблему или задайте вопрос</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`support-page-message ${msg.is_admin ? 'admin' : 'user'}`}>
                  <div className="msg-avatar">
                    <i className={`fa-solid ${msg.is_admin ? 'fa-headset' : 'fa-user'}`}></i>
                  </div>
                  <div className="msg-content">
                    <div className="msg-sender">{msg.is_admin ? 'Поддержка' : 'Вы'}</div>
                    <div className="msg-text">{msg.message}</div>
                    <div className="msg-time">{new Date(msg.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          <div className="support-page-input">
            <input 
              type="text" 
              value={newMessage} 
              onChange={e => setNewMessage(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && sendMessage()}
              placeholder="Введите сообщение..."
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !newMessage.trim()}>
              <i className="fa-solid fa-paper-plane"></i> Отправить
            </button>
          </div>
        </div>
        
        <div className="support-info">
          <div className="support-info-item">
            <i className="fa-brands fa-telegram"></i>
            <div>
              <h4>Telegram</h4>
              <a href="https://t.me/easymoneycas_bot" target="_blank" rel="noopener noreferrer">@easymoneycaspro</a>
            </div>
          </div>
          <div className="support-info-item">
            <i className="fa-solid fa-clock"></i>
            <div>
              <h4>Время ответа</h4>
              <span>Обычно в течение 1 часа</span>
            </div>
          </div>
          <div className="support-info-item vip">
            <i className="fa-solid fa-star"></i>
            <div>
              <h4>VIP Поддержка</h4>
              <span>Сотрудничество и проблемы с платежами</span>
              <a href="https://t.me/easymoneysupportvip" target="_blank" rel="noopener noreferrer">@easymoneysupportvip</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};


const PolicyPage = () => (
  <div className="page legal-page" data-testid="policy-page">
    <div className="legal-content">
      <h1><i className="fa-solid fa-shield-halved"></i> Политика конфиденциальности</h1>
      
      <section>
        <h3>1. Какая информация подлежит сбору</h3>
        <p>1.1. Сбору подлежат только сведения, обеспечивающие возможность поддержки обратной связи с пользователем.</p>
        <p>1.2. Некоторые действия пользователей автоматически сохраняются в журналах сервера:</p>
        <p>1.2.1. IP-адрес, данные о типе браузера;</p>
        <p>1.2.2. Надстройках, времени запроса и т. д.</p>
      </section>
      
      <section>
        <h3>2. Как используется полученная информация</h3>
        <p>2.1. Сведения, предоставленные пользователем, используются для связи с ним, в том числе для направления уведомлений.</p>
      </section>
      
      <section>
        <h3>3. Управление личными данными</h3>
        <p>3.1. Личные данные доступны для просмотра, изменения и удаления в личном кабинете пользователя.</p>
        <p>3.2. В целях предотвращения случайного удаления или повреждения данных информация хранится в резервных копиях в течение 7 дней и может быть восстановлена по запросу пользователя.</p>
      </section>
      
      <section>
        <h3>4. Предоставление данных третьим лицам</h3>
        <p>4.1. Личные данные пользователей могут быть переданы лицам, не связанным с настоящим сайтом, если это необходимо:</p>
        <p>4.1.1. Для соблюдения закона, нормативно-правового акта, исполнения решения суда;</p>
        <p>4.1.2. Для выявления или воспрепятствования мошенничеству;</p>
        <p>4.1.3. Для устранения технических неисправностей в работе сайта;</p>
        <p>4.1.4. Для предоставления информации на основании запроса уполномоченных государственных органов.</p>
      </section>
      
      <section>
        <h3>5. Безопасность данных</h3>
        <p>5.1. Администрация сайта принимает все меры для защиты данных пользователей от несанкционированного доступа.</p>
      </section>
      
      <section>
        <h3>6. Изменения</h3>
        <p>6.1. Обновления политики конфиденциальности публикуются на данной странице.</p>
      </section>
    </div>
  </div>
);

// Terms Page
const TermsPage = () => (
  <div className="page legal-page" data-testid="terms-page">
    <div className="legal-content">
      <h1><i className="fa-solid fa-file-contract"></i> Пользовательское соглашение</h1>
      
      <div className="legal-warning">
        <i className="fa-solid fa-exclamation-triangle"></i>
        Если Вы не согласны с условиями настоящего Пользовательского Соглашения, не авторизуйтесь на Сайте EASY MONEY и не используйте сервисы данного Сайта.
      </div>
      
      <section>
        <h3>1. Термины и определения</h3>
        <p>1.1.1 <strong>Сайт</strong> - совокупность информации, текстов, графических элементов, дизайна, изображений и иных результатов интеллектуальной деятельности, доступных по адресу EASY MONEY.</p>
        <p>1.1.2 <strong>Соглашение</strong> – настоящее Пользовательское Соглашение, являющееся Публичной офертой.</p>
        <p>1.1.3 <strong>Администратор</strong> – лицо, в коммерческом управлении которого находится Сайт.</p>
        <p>1.1.4 <strong>Пользователь</strong> – лицо, заключившее с Администратором Соглашение путем акцепта настоящей оферты.</p>
        <p>1.1.5 <strong>Монеты</strong> – виртуальная игровая единица Сайта, используемая для получения Услуги.</p>
      </section>
      
      <section>
        <h3>2. Предмет соглашения</h3>
        <p>2.1 Предметом настоящего Соглашения является предложение Администратора получать с использованием сервисов Сайта развлекательно-аттракционные Услуги.</p>
        <p>2.2 Лицо, акцептовавшее настоящую оферту, становится Пользователем и обязуется использовать Сайт только на условиях настоящего Соглашения.</p>
        <p>2.3 Пользование Услугами Сайта лицами, не обладающими полной дееспособностью, ЗАПРЕЩЕНО.</p>
      </section>
      
      <section>
        <h3>3. Услуги сайта</h3>
        <p>4.1 Услуги, оказываемые на Сайте, являются зрелищно-развлекательными и аттракционными (программа-симулятор).</p>
        <p>4.2 Неиспользованные виртуальные игровые единицы могут быть возвращены пользователю в соответствии со стоимостью их приобретения.</p>
      </section>
      
      <section>
        <h3>4. Порядок пользования</h3>
        <p>5.4 Запрещается использовать автокликер при игре на Сайте. При нарушении вы будете заблокированы.</p>
        <p>5.12 Пользователям ЗАПРЕЩЕНО регистрировать более 1 учетной записи без предварительного согласования с администрацией.</p>
        <p>5.17 ЗАПРЕЩЕНО промывать средства через перевод либо переводить с мультиаккаунтов на чистый аккаунт.</p>
      </section>
      
      <section>
        <h3>5. Оплата</h3>
        <p>6.1 Цены за монеты на Сайте устанавливаются Администратором и могут быть изменены по решению Администратора.</p>
        <p>6.6 Все оплаченные Услуги Сайта являются добровольными пожертвованиями со стороны Пользователя.</p>
      </section>
      
      <section>
        <h3>6. Ответственность</h3>
        <p>8.1 В случае нарушения Пользователем условий настоящего Соглашения, Администратор вправе заблокировать или удалить с Сайта аккаунт Пользователя.</p>
        <p>8.2 Администратор не отвечает за работоспособность Сайта и не гарантирует его бесперебойной работы.</p>
      </section>
    </div>
  </div>
);

// Admin Panel
const AdminLogin = () => {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const login = async () => {
    setLoading(true);
    try {
      const res = await api.post('/admin/login', { password });
      if (res.data.success) {
        localStorage.setItem('adminToken', res.data.token);
        navigate('/apminpannelonlyadmins/dashboard');
      }
    } catch (e) {
      toast.error('Неверный пароль');
    }
    setLoading(false);
  };

  return (
    <div className="admin-login" data-testid="admin-login">
      <div className="admin-login-card">
        <img src="/logo.png" alt="EASY MONEY" />
        <h2>Админ панель</h2>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Пароль" data-testid="admin-password" />
        <button onClick={login} disabled={loading} data-testid="admin-login-btn">
          {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : 'Войти'}
        </button>
      </div>
    </div>
  );
};


// Support Admin Panel Component
const SupportAdminPanel = ({ adminApi }) => {
  const [chats, setChats] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [replyText, setReplyText] = useState('');

  useEffect(() => {
    fetchChats();
    const interval = setInterval(fetchChats, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedUser) {
      fetchMessages();
      const interval = setInterval(fetchMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedUser]);

  const fetchChats = async () => {
    try {
      const res = await adminApi.get('/admin/support/chats');
      if (res.data.success) setChats(res.data.chats);
    } catch (e) {}
  };

  const fetchMessages = async () => {
    if (!selectedUser) return;
    try {
      const res = await adminApi.get(`/admin/support/messages/${selectedUser._id}`);
      if (res.data.success) setMessages(res.data.messages);
    } catch (e) {}
  };

  const sendReply = async () => {
    if (!replyText.trim() || !selectedUser) return;
    try {
      await adminApi.post(`/admin/support/reply/${selectedUser._id}`, { message: replyText });
      setReplyText('');
      fetchMessages();
      fetchChats();
      toast.success('Ответ отправлен');
    } catch (e) {
      toast.error('Ошибка отправки');
    }
  };

  return (
    <div className="support-admin-container">
      <div className="support-chats-list">
        <h3>Чаты ({chats.length})</h3>
        {chats.map((chat, i) => (
          <div 
            key={i} 
            className={`chat-item ${selectedUser?._id === chat._id ? 'active' : ''} ${chat.unread_count > 0 ? 'unread' : ''}`}
            onClick={() => setSelectedUser(chat)}
          >
            <div className="chat-name">
              <span className="chat-reg-number" style={{color: '#6366f1', fontWeight: 'bold', marginRight: '8px'}}>
                #{chat.registration_number || '?'}
              </span>
              {chat.user_name}
            </div>
            <div className="chat-preview">{chat.last_message?.substring(0, 50)}...</div>
            <div className="chat-meta">
              <span className="chat-time">{new Date(chat.last_time).toLocaleTimeString()}</span>
              {chat.unread_count > 0 && <span className="chat-badge">{chat.unread_count}</span>}
            </div>
          </div>
        ))}
      </div>
      <div className="support-chat-window">
        {selectedUser ? (
          <>
            <div className="chat-header">
              <h3>
                <span style={{color: '#6366f1', marginRight: '10px'}}>#{selectedUser.registration_number || '?'}</span>
                {selectedUser.user_name}
              </h3>
              <div style={{fontSize: '12px', color: '#888', marginTop: '5px'}}>
                <span style={{marginRight: '15px'}}>Баланс: <b style={{color: '#10b981'}}>{selectedUser.user_balance?.toFixed(2) || 0}₽</b></span>
                <span>Депозит: <b style={{color: '#f59e0b'}}>{selectedUser.user_deposit?.toFixed(2) || 0}₽</b></span>
              </div>
              <small style={{display: 'block', marginTop: '3px'}}>ID: {selectedUser._id}</small>
            </div>
            <div className="chat-messages">
              {messages.map((msg, i) => (
                <div key={i} className={`chat-message ${msg.is_admin ? 'admin' : 'user'}`}>
                  <div className="msg-sender">{msg.is_admin ? '👨‍💼 Поддержка' : '👤 Пользователь'}</div>
                  <div className="msg-text">{msg.message}</div>
                  <div className="msg-time">{new Date(msg.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
            <div className="chat-reply">
              <textarea 
                value={replyText} 
                onChange={e => setReplyText(e.target.value)}
                placeholder="Введите ответ..."
                rows="3"
              />
              <button onClick={sendReply} disabled={!replyText.trim()}>
                <i className="fa-solid fa-paper-plane"></i> Отправить
              </button>
            </div>
          </>
        ) : (
          <div className="no-chat-selected">
            <i className="fa-solid fa-comments"></i>
            <p>Выберите чат из списка</p>
          </div>
        )}
      </div>
    </div>
  );
};


const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [withdraws, setWithdraws] = useState([]);
  const [promos, setPromos] = useState([]);
  const [tab, setTab] = useState('stats');
  const [search, setSearch] = useState('');
  const [newPromo, setNewPromo] = useState({ name: '', reward: 100, limit: 100, type: 0, deposit_required: false, wager_multiplier: 3, bonus_percent: 0 });
  const [rtpSettings, setRtpSettings] = useState({});
  const [editingUser, setEditingUser] = useState(null);
  const [manualDepositAmount, setManualDepositAmount] = useState(150);
  const navigate = useNavigate();

  const adminApi = axios.create({ baseURL: API });
  adminApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('adminToken');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (!token) navigate('/apminpannelonlyadmins');
    fetchData();
  }, [tab]);

  const fetchData = async () => {
    try {
      if (tab === 'stats' || tab === 'rtp') {
        const res = await adminApi.get('/admin/stats');
        if (res.data.success) {
          setStats(res.data);
          setRtpSettings(res.data.settings || {});
        }
      } else if (tab === 'users') {
        const res = await adminApi.get(`/admin/users?search=${encodeURIComponent(search)}`);
        if (res.data.success) setUsers(res.data.users);
      } else if (tab === 'withdraws') {
        const res = await adminApi.get('/admin/withdraws');
        if (res.data.success) setWithdraws(res.data.withdraws);
      } else if (tab === 'promos') {
        const res = await adminApi.get('/admin/promos');
        if (res.data.success) setPromos(res.data.promos);
      } else if (tab === 'support') {
        // Support data fetched within SupportAdminPanel component
      }
    } catch (e) {
      if (e.response?.status === 401) {
        localStorage.removeItem('adminToken');
        navigate('/apminpannelonlyadmins');
      }
    }
  };

  const updateWithdraw = async (id, status) => {
    try {
      await adminApi.put(`/admin/withdraw/${id}`, { status });
      toast.success(status === 'completed' ? 'Вывод одобрен' : 'Вывод отклонен');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const createPromo = async () => {
    try {
      await adminApi.post('/admin/promo', newPromo);
      toast.success('Промокод создан');
      setNewPromo({ name: '', reward: 100, limit: 100, type: 0, deposit_required: false, wager_multiplier: 3, bonus_percent: 0 });
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
  };

  const updateRTP = async () => {
    try {
      await adminApi.put('/admin/rtp', rtpSettings);
      toast.success('RTP обновлен');
    } catch (e) {
      toast.error('Ошибка');
    }
  };

  const updateUser = async () => {
    if (!editingUser) return;
    try {
      await adminApi.put('/admin/user', editingUser);
      toast.success('Пользователь обновлен');
      setEditingUser(null);
      fetchData();
    } catch (e) {
      toast.error('Ошибка');
    }
  };

  const addManualDeposit = async () => {
    if (!editingUser || !manualDepositAmount || manualDepositAmount < 1) {
      toast.error('Введите корректную сумму');
      return;
    }
    try {
      await adminApi.post('/admin/manual-deposit', { 
        user_id: editingUser.user_id, 
        amount: manualDepositAmount 
      });
      toast.success(`Депозит ${manualDepositAmount}₽ добавлен`);
      setManualDepositAmount(150);
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка добавления депозита');
    }
  };

  const logout = () => {
    localStorage.removeItem('adminToken');
    navigate('/apminpannelonlyadmins');
  };

  const promoTypes = ['Баланс', 'Бонус к депозиту %', 'Фриспины', 'Без вейджера', 'Кешбэк'];

  return (
    <div className="admin-dashboard" data-testid="admin-dashboard">
      <div className="admin-sidebar">
        <div className="admin-logo">
          <img src="/logo.png" alt="EASY MONEY" />
          <span>Admin</span>
        </div>
        <nav>
          <button className={tab === 'stats' ? 'active' : ''} onClick={() => setTab('stats')}><i className="fa-solid fa-chart-pie"></i> Статистика</button>
          <button className={tab === 'rtp' ? 'active' : ''} onClick={() => setTab('rtp')}><i className="fa-solid fa-percent"></i> RTP</button>
          <button className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}><i className="fa-solid fa-users"></i> Пользователи</button>
          <button className={tab === 'withdraws' ? 'active' : ''} onClick={() => setTab('withdraws')}><i className="fa-solid fa-money-bill-transfer"></i> Выводы</button>
          <button className={tab === 'promos' ? 'active' : ''} onClick={() => setTab('promos')}><i className="fa-solid fa-ticket"></i> Промокоды</button>
          <button className={tab === 'support' ? 'active' : ''} onClick={() => setTab('support')}><i className="fa-solid fa-headset"></i> Поддержка</button>
          <button onClick={logout}><i className="fa-solid fa-sign-out"></i> Выход</button>
        </nav>
      </div>

      <div className="admin-content">
        {tab === 'stats' && stats && (
          <div className="admin-stats" data-testid="admin-stats">
            <h2>Статистика</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <h4>Депозиты сегодня</h4>
                <div className="stat-value">{stats.payments.today?.toFixed(2)} ₽</div>
              </div>
              <div className="stat-card">
                <h4>Депозиты за неделю</h4>
                <div className="stat-value">{stats.payments.week?.toFixed(2)} ₽</div>
              </div>
              <div className="stat-card">
                <h4>Депозиты всего</h4>
                <div className="stat-value">{stats.payments.all?.toFixed(2)} ₽</div>
              </div>
              <div className="stat-card">
                <h4>Ожидающие выводы</h4>
                <div className="stat-value">{stats.withdrawals.pending_count} ({stats.withdrawals.pending_sum?.toFixed(2)} ₽)</div>
              </div>
              <div className="stat-card">
                <h4>Пользователей</h4>
                <div className="stat-value">{stats.users.all}</div>
              </div>
              <div className="stat-card">
                <h4>Новых сегодня</h4>
                <div className="stat-value">{stats.users.today}</div>
              </div>
            </div>
          </div>
        )}

        {tab === 'rtp' && (
          <div className="admin-rtp" data-testid="admin-rtp">
            <h2>Настройки RTP (Return To Player)</h2>
            <p className="rtp-desc">RTP определяет процент возврата игроку. Чем выше RTP, тем чаще игроки выигрывают.</p>
            <div className="rtp-grid">
              {['dice', 'mines', 'bubbles', 'tower', 'crash', 'x100'].map(game => (
                <div key={game} className="rtp-item">
                  <label>{game.charAt(0).toUpperCase() + game.slice(1)} RTP</label>
                  <div className="rtp-input">
                    <input 
                      type="range" 
                      min="10" 
                      max="99.9" 
                      step="0.1"
                      value={rtpSettings[`${game}_rtp`] || 97}
                      onChange={e => setRtpSettings({...rtpSettings, [`${game}_rtp`]: parseFloat(e.target.value)})}
                    />
                    <span>{rtpSettings[`${game}_rtp`] || 97}%</span>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn-save-rtp" onClick={updateRTP}>Сохранить RTP</button>
          </div>
        )}

        {tab === 'users' && (
          <div className="admin-users" data-testid="admin-users">
            <h2>Пользователи</h2>
            <div className="search-container" style={{display: 'flex', gap: '10px', marginBottom: '15px'}}>
              <input 
                type="text" 
                value={search} 
                onChange={e => setSearch(e.target.value)} 
                onKeyUp={e => e.key === 'Enter' && fetchData()} 
                placeholder="Поиск по номеру (#123), имени или ID..." 
                style={{flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid #333', background: '#1a1a2e', color: '#fff'}}
              />
              <button onClick={fetchData} style={{padding: '12px 20px', background: '#6366f1', border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer'}}>
                🔍 Найти
              </button>
            </div>
            
            {editingUser && (
              <div className="edit-user-modal">
                <div className="edit-user-content">
                  <h3>Редактирование: {editingUser.name}</h3>
                  <div className="edit-field">
                    <label>Баланс</label>
                    <input type="number" value={editingUser.balance || 0} onChange={e => setEditingUser({...editingUser, balance: +e.target.value})} />
                  </div>
                  <div className="edit-field">
                    <label>Drain</label>
                    <input type="checkbox" checked={editingUser.is_drain || false} onChange={e => setEditingUser({...editingUser, is_drain: e.target.checked})} />
                  </div>
                  <div className="edit-field">
                    <label>Drain %</label>
                    <input type="number" value={editingUser.is_drain_chance || 20} onChange={e => setEditingUser({...editingUser, is_drain_chance: +e.target.value})} />
                  </div>
                  <div className="edit-field">
                    <label>Youtuber</label>
                    <input type="checkbox" checked={editingUser.is_youtuber || false} onChange={e => setEditingUser({...editingUser, is_youtuber: e.target.checked})} />
                  </div>
                  <div className="edit-field">
                    <label>Бан</label>
                    <input type="checkbox" checked={editingUser.is_ban || false} onChange={e => setEditingUser({...editingUser, is_ban: e.target.checked})} />
                  </div>
                  
                  <hr style={{margin: '20px 0', border: '1px solid #333'}} />
                  
                  <div className="edit-field">
                    <label>Ручной депозит (пополнение)</label>
                    <input 
                      type="number" 
                      value={manualDepositAmount} 
                      onChange={e => setManualDepositAmount(+e.target.value)} 
                      placeholder="Сумма депозита"
                      min="1"
                    />
                    <button 
                      onClick={addManualDeposit} 
                      className="btn-manual-deposit"
                      style={{marginTop: '10px', background: '#10b981', padding: '10px 20px'}}
                    >
                      💰 Добавить депозит
                    </button>
                    <small style={{color: '#888', display: 'block', marginTop: '5px'}}>
                      Депозит будет добавлен на баланс и в total_deposited. Пользователь сможет выводить средства.
                    </small>
                  </div>
                  
                  <div className="edit-buttons">
                    <button onClick={updateUser}>Сохранить</button>
                    <button onClick={() => setEditingUser(null)}>Отмена</button>
                  </div>
                </div>
              </div>
            )}
            
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>Баланс</th>
                  <th>Депозит</th>
                  <th>IP</th>
                  <th>Дата</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className={u.is_ban ? 'banned' : ''}>
                    <td>#{u.registration_number || 'N/A'}</td>
                    <td>{u.name} {u.is_youtuber && '⭐'} {u.is_drain && '🎯'}</td>
                    <td>{u.balance?.toFixed(2)} ₽</td>
                    <td>{u.deposit?.toFixed(2)} ₽</td>
                    <td>{u.register_ip || '-'}</td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    <td>
                      <button className="btn-edit" onClick={() => setEditingUser({user_id: u.id, ...u})}>✏️</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'withdraws' && (
          <div className="admin-withdraws" data-testid="admin-withdraws">
            <h2>Заявки на вывод</h2>
            <table>
              <thead>
                <tr>
                  <th>Пользователь</th>
                  <th>Сумма</th>
                  <th>Способ</th>
                  <th>Реквизиты</th>
                  <th>Баланс</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {withdraws.map(w => (
                  <tr key={w.id}>
                    <td>{w.user_name}</td>
                    <td>{w.amount?.toFixed(2)} ₽</td>
                    <td>
                      <span className="withdraw-method">
                        {w.system === 'card' ? '💳 Карта' : 
                         w.system === 'sbp' ? '📱 СБП' : 
                         w.system?.startsWith('crypto_') ? `🪙 ${w.system.replace('crypto_', '').toUpperCase()}` : w.system}
                        {w.bank_name && <small><br/>{w.bank_name}</small>}
                        {w.crypto_network && <small><br/>Сеть: {w.crypto_network}</small>}
                      </span>
                    </td>
                    <td className="wallet-cell">{w.wallet}</td>
                    <td>{w.user_balance?.toFixed(2)} ₽</td>
                    <td>
                      <button className="btn-approve" onClick={() => updateWithdraw(w.id, 'completed')} title="Одобрить">✓</button>
                      <button className="btn-reject" onClick={() => updateWithdraw(w.id, 'rejected')} title="Отклонить">✗</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'promos' && (
          <div className="admin-promos" data-testid="admin-promos">
            <h2>Промокоды</h2>
            <div className="promo-form-advanced">
              <div className="promo-row">
                <input type="text" value={newPromo.name} onChange={e => setNewPromo({...newPromo, name: e.target.value})} placeholder="Название" />
                <select value={newPromo.type} onChange={e => setNewPromo({...newPromo, type: +e.target.value})}>
                  {promoTypes.map((t, i) => <option key={i} value={i}>{t}</option>)}
                </select>
              </div>
              <div className="promo-row">
                <input type="number" value={newPromo.reward} onChange={e => setNewPromo({...newPromo, reward: +e.target.value})} placeholder="Награда ₽" />
                <input type="number" value={newPromo.limit} onChange={e => setNewPromo({...newPromo, limit: +e.target.value})} placeholder="Лимит" />
              </div>
              <div className="promo-row">
                <input type="number" value={newPromo.wager_multiplier} onChange={e => setNewPromo({...newPromo, wager_multiplier: +e.target.value})} placeholder="Вейджер x" />
                <input type="number" value={newPromo.bonus_percent} onChange={e => setNewPromo({...newPromo, bonus_percent: +e.target.value})} placeholder="Бонус к депозиту %" />
              </div>
              <div className="promo-row">
                <label><input type="checkbox" checked={newPromo.deposit_required} onChange={e => setNewPromo({...newPromo, deposit_required: e.target.checked})} /> Требуется депозит</label>
                <button onClick={createPromo}>Создать</button>
              </div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Тип</th>
                  <th>Награда</th>
                  <th>Вейджер</th>
                  <th>Использовано</th>
                </tr>
              </thead>
              <tbody>
                {promos.map(p => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td>{promoTypes[p.type] || 'Баланс'}</td>
                    <td>{p.type === 1 ? `${p.bonus_percent}%` : `${p.reward}₽`}</td>
                    <td>x{p.wager_multiplier || 3}</td>
                    <td>{p.limited}/{p.limit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'support' && (
          <div className="admin-support" data-testid="admin-support">
            <h2>Поддержка пользователей</h2>
            <SupportAdminPanel adminApi={adminApi} />
          </div>
        )}

      </div>
    </div>
  );
};

// ============== SLOTS PAGE ==============
const SlotsPage = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const navigate = useNavigate();

  useEffect(() => {
    fetchGames();
  }, [page, search]);

  const fetchGames = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/slots/games?page=${page}&limit=50&search=${search}`);
      if (res.data.success) {
        setGames(res.data.games);
        setTotalPages(res.data.pages);
      }
    } catch (e) {
      toast.error('Ошибка загрузки игр');
    }
    setLoading(false);
  };

  return (
    <div className="slots-page" data-testid="slots-page">
      <div className="slots-header">
        <h1><i className="fa-solid fa-slot-machine"></i> 🎰 Слоты</h1>
        <p>Более 3000 игр от лучших провайдеров</p>
        <div className="slots-search">
          <input 
            type="text" 
            placeholder="Поиск игр..." 
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
          <i className="fa-solid fa-search"></i>
        </div>
      </div>
      
      {loading ? (
        <div className="loading"><i className="fa-solid fa-spinner fa-spin"></i> Загрузка...</div>
      ) : (
        <>
          <div className="slots-grid">
            {games.map(game => (
              <div key={game.id} 
                className="slot-card"
                onClick={() => navigate(`/slots/${game.name}`)}
                data-testid={`slot-${game.name}`}
              >
                <div className="slot-img" style={{background: `linear-gradient(135deg, hsl(${game.id * 37 % 360}, 70%, 30%), hsl(${game.id * 73 % 360}, 60%, 20%))`}}>
                  <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '40px'}}>
                    🎰
                  </div>
                </div>
                <div className="slot-info">
                  <h3>{game.title}</h3>
                </div>
              </div>
            ))}
          </div>
          
          {totalPages > 1 && (
            <div className="slots-pagination">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))} 
                disabled={page === 1}
              >
                ← Назад
              </button>
              <span>Страница {page} из {totalPages}</span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))} 
                disabled={page === totalPages}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Slot Game Component (iframe to PHP)
const SlotGame = () => {
  const { gameName } = useParams();
  const { user } = useAuth();
  const [gameUrl, setGameUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [gameInfo, setGameInfo] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      toast.error('Войдите для игры в слоты');
      navigate('/login');
      return;
    }
    startGame();
  }, [gameName, user]);

  const startGame = async () => {
    setLoading(true);
    try {
      // Get game info
      const infoRes = await api.get(`/slots/game/${gameName}`);
      if (infoRes.data.success) {
        setGameInfo(infoRes.data.game);
      }
      
      // Create session
      const res = await api.post('/slots/session', { game_name: gameName });
      if (res.data.success) {
        setGameUrl(res.data.game_url);
      } else {
        toast.error('Ошибка запуска игры');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка запуска игры');
    }
    setLoading(false);
  };

  return (
    <div className="slot-game-page" data-testid="slot-game-page">
      <div className="slot-game-header">
        <button onClick={() => navigate('/slots')} className="back-btn">
          <i className="fa-solid fa-arrow-left"></i> Назад к слотам
        </button>
        {gameInfo && <h2>{gameInfo.title}</h2>}
        {user && <span className="balance-info">Баланс: {user.balance?.toFixed(2)}₽</span>}
      </div>
      
      {loading ? (
        <div className="loading"><i className="fa-solid fa-spinner fa-spin"></i> Загрузка игры...</div>
      ) : gameUrl ? (
        <div className="slot-game-container">
          <iframe 
            src={gameUrl} 
            title={gameInfo?.title || 'Slot Game'}
            allowFullScreen
          />
        </div>
      ) : (
        <div className="error">Не удалось загрузить игру</div>
      )}
    </div>
  );
};

// Protected Route
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading"><i className="fa-solid fa-spinner fa-spin"></i></div>;
  if (!user) return <Navigate to="/login" />;
  return children;
};

// Main App
function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
    // Save ref code from URL to localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const refCode = urlParams.get('ref');
    if (refCode) {
      localStorage.setItem('ref_code', refCode);
    }
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const res = await api.get('/auth/me');
        if (res.data.success) setUser(res.data.user);
      } catch (e) {
        localStorage.removeItem('token');
      }
    }
    setLoading(false);
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    localStorage.removeItem('ref_code'); // Clear ref code after successful login
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const updateBalance = (newBalance) => {
    setUser(prev => prev ? { ...prev, balance: newBalance } : null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateBalance }}>
      <BrowserRouter>
        <div className="App">
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/apminpannelonlyadmins" element={<AdminLogin />} />
            <Route path="/apminpannelonlyadmins/dashboard" element={<AdminDashboard />} />
            <Route path="/*" element={
              <>
                <Header />
                <main>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/mines" element={<MinesGame />} />
                    <Route path="/dice" element={<DiceGame />} />
                    <Route path="/bubbles" element={<BubblesGame />} />
                    <Route path="/tower" element={<TowerGame />} />
                    <Route path="/crash" element={<CrashGame />} />
                    <Route path="/x100" element={<X100Game />} />
                    <Route path="/policy" element={<PolicyPage />} />
                    <Route path="/terms" element={<TermsPage />} />
                    <Route path="/wallet" element={<ProtectedRoute><Wallet /></ProtectedRoute>} />
                    <Route path="/payment/success" element={<PaymentSuccess />} />
                    <Route path="/payment/failed" element={<PaymentFailed />} />
                    <Route path="/bonus" element={<ProtectedRoute><Bonus /></ProtectedRoute>} />
                    <Route path="/ref" element={<ProtectedRoute><Referral /></ProtectedRoute>} />
                    <Route path="/support" element={<ProtectedRoute><SupportPage /></ProtectedRoute>} />
                    <Route path="/slots" element={<SlotsPage />} />
                    <Route path="/slots/:gameName" element={<SlotGame />} />
                  </Routes>
                </main>
                <Footer />
                <SupportChat />
              </>
            } />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
