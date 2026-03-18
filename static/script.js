// --- Status Update ---
function updateStatus() {
    fetch('/api/status/all')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching status:', response.status, response.statusText);
                const tradingStatusSpan = document.getElementById('tradingStatus');
                const llmStatusSpan = document.getElementById('llmStatus');
                if (tradingStatusSpan) tradingStatusSpan.textContent = 'API Error';
                if (llmStatusSpan) llmStatusSpan.textContent = 'API Error';
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => {
            const tradingStatusSpan = document.getElementById('tradingStatus');
            const llmStatusSpan = document.getElementById('llmStatus');
            const tradingLogsTimestampSpan = document.getElementById('tradingLogsTimestamp');

            if (tradingStatusSpan) {
                const tradingInfo = data.trading || {};
                tradingStatusSpan.textContent = tradingInfo.status || 'N/A';
                if (tradingInfo.last_update && tradingLogsTimestampSpan) {
                    try {
                        tradingLogsTimestampSpan.textContent = `Last update: ${new Date(tradingInfo.last_update).toLocaleString()}`;
                    } catch (e) {
                        console.error("Error formatting timestamp:", tradingInfo.last_update, e);
                        tradingLogsTimestampSpan.textContent = 'Last update: invalid date';
                    }
                }
            }

            if (llmStatusSpan) {
                const llmInfo = data.llm_generator || {};
                llmStatusSpan.textContent = llmInfo.status || 'N/A';
            }
        })
        .catch(error => {
            console.error('Error in updateStatus fetch:', error);
            const tradingStatusSpan = document.getElementById('tradingStatus');
            const llmStatusSpan = document.getElementById('llmStatus');
            if (tradingStatusSpan) tradingStatusSpan.textContent = 'Error';
            if (llmStatusSpan) llmStatusSpan.textContent = 'Error';
        });
}

// --- Trade Progress Update ---
function updateTradeProgress() {
    fetch('/api/trading/progress')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching trade progress:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => {
            const tradesByStrategy = {};
            if (data && data.trades && Array.isArray(data.trades) && data.trades.length > 0) {
                data.trades.forEach(trade => {
                    const strategyName = trade.strategy_name || 'Unknown Strategy';
                    if (!tradesByStrategy[strategyName]) {
                        tradesByStrategy[strategyName] = [];
                    }
                    tradesByStrategy[strategyName].push(trade);
                });
            }

            const llmStrategiesContainer = document.getElementById('llmStrategiesContainer');
            llmStrategiesContainer.innerHTML = '<h4>Available Strategies & Trade Progress:</h4>';

            fetch('/api/llm/strategies')
                .then(response => {
                    if (!response.ok) {
                        console.error('Error fetching LLM strategies:', response.status, response.statusText);
                        llmStrategiesContainer.innerHTML += '<p>Failed to load LLM strategies.</p>';
                        return Promise.reject(response);
                    }
                    return response.json();
                })
                .then(strategies => {
                    if (strategies && strategies.length > 0) {
                        strategies.forEach(strategy => {
                            const strategyDiv = document.createElement('div');
                            strategyDiv.className = 'strategy-section';

                            let progressHtml = '<p><strong>Trade Progress:</strong> No active trades for this strategy.</p>';
                            const strategyName = strategy.strategy_name;

                            if (tradesByStrategy[strategyName] && tradesByStrategy[strategyName].length > 0) {
                                progressHtml = '<h5>Active Trades:</h5>';
                                tradesByStrategy[strategyName].forEach(trade => {
                                    progressHtml += `
                                        <div class="trade-item">
                                            <strong>Symbol:</strong> ${trade.symbol || 'N/A'} |
                                            <strong>Investment:</strong> $${trade.investment_usd?.toFixed(2) ?? 'N/A'} |
                                            <strong>Status:</strong> ${trade.status || 'unknown'} |
                                            <strong>P&L:</strong> $${trade.pnl_usd?.toFixed(2) ?? 'N/A'}
                                            <strong>Buy Price:</strong> ${trade.buy_price?.toFixed(4) ?? 'N/A'} |
                                            <strong>Sell Price:</strong> ${trade.sell_price?.toFixed(4) ?? 'N/A'} |
                                            <strong>Bought:</strong> ${trade.buy_timestamp ? new Date(trade.buy_timestamp).toLocaleString() : 'N/A'} |
                                            <strong>Sold:</strong> ${trade.sell_timestamp ? new Date(trade.sell_timestamp).toLocaleString() : 'N/A'}
                                        </div>`;
                                });
                            }

                            strategyDiv.innerHTML = `
                                <h4>${strategy.strategy_name} (${strategy.symbol})</h4>
                                <p><strong>LLM Provider:</strong> ${strategy.llm_provider || 'N/A'}</p>
                                <p><strong>Model:</strong> ${strategy.model || 'N/A'}</p>
                                <p><strong>Description:</strong> ${strategy.description}</p>
                                <p><strong>Risk:</strong> Stop Loss ${(strategy.risk_parameters?.stop_loss_pct * 100)?.toFixed(2) ?? 'N/A'}%, Take Profit ${(strategy.risk_parameters?.take_profit_pct * 100)?.toFixed(2) ?? 'N/A'}%</p>
                                <p><strong>Rationale:</strong> ${strategy.profit_rationale}</p>
                                ${progressHtml}
                            `;
                            llmStrategiesContainer.appendChild(strategyDiv);
                        });
                    } else {
                        llmStrategiesContainer.innerHTML += '<p>No strategies generated yet. Click "Generate LLM Strategies" to fetch them.</p>';
                    }
                })
                .catch(error => {
                    console.error('Error fetching LLM strategies after progress update:', error);
                    llmStrategiesContainer.innerHTML = '<h4>Available Strategies & Trade Progress:</h4><p>Could not load LLM strategies. Please check console for errors.</p>';
                });
        })
        .catch(error => {
            console.error('Error fetching trade progress:', error);
            document.getElementById('llmStrategiesContainer').innerHTML = '<h4>Available Strategies & Trade Progress:</h4><p>Could not load trade progress. Please check console for errors.</p>';
        });
}

// --- Configuration Update Function ---
function saveTradingConfig() {
    const capitalInput = document.getElementById('configCapital');
    const tradeSizeInput = document.getElementById('configTradeSize');
    const stopLossInput = document.getElementById('configStopLoss');
    const takeProfitInput = document.getElementById('configTakeProfit');

    const config = {
        capital: parseFloat(capitalInput.value),
        trade_size_usd: parseFloat(tradeSizeInput.value),
        stop_loss_pct: parseFloat(stopLossInput.value),
        take_profit_pct: parseFloat(takeProfitInput.value)
    };

    if (isNaN(config.capital) || isNaN(config.trade_size_usd) || isNaN(config.stop_loss_pct) || isNaN(config.take_profit_pct)) {
        alert('Please enter valid numbers for all trading parameters.');
        return;
    }

    fetch('/api/trading/configure', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
    })
    .then(response => {
        if (!response.ok) {
            console.error('Save config returned error:', response.status, response.statusText);
            return response.text().then(text => { throw new Error(text || 'Failed to save config') });
        }
        return response.json();
    })
    .then(data => {
        console.log('Save config response:', data);
        alert(data.message || 'Configuration saved successfully!');
        updateStatus();
    })
    .catch(error => {
        console.error('Error saving trading configuration:', error);
        alert(`Failed to save configuration: ${error.message}. Please check the console for details.`);
    });
}

// --- Initial Load and Periodic Updates ---
document.addEventListener('DOMContentLoaded', () => {
    const tradingStatusSpan = document.getElementById('tradingStatus');
    const llmStatusSpan = document.getElementById('llmStatus');
    const tradingLogsPre = document.getElementById('tradingLogs');
    const llmLogsPre = document.getElementById('llmLogs');
    const statusUpdatesPre = document.getElementById('statusUpdates');
    const tradingLogsTimestampSpan = document.getElementById('tradingLogsTimestamp');

    const startTradingBtn = document.getElementById('startTradingBtn');
    const stopTradingBtn = document.getElementById('stopTradingBtn');
    const generateLlmStrategiesBtn = document.getElementById('triggerLlmGenBtn');
    const saveTradingConfigBtn = document.getElementById('saveTradingConfigBtn');
    const resetConfigBtn = document.getElementById('resetConfigBtn');

    const capitalInput = document.getElementById('configCapital');
    const tradeSizeInput = document.getElementById('configTradeSize');
    const stopLossInput = document.getElementById('configStopLoss');
    const takeProfitInput = document.getElementById('configTakeProfit');

    function initializeUI() {
        updateStatus();

        fetch('/api/trading/configure', { method: 'GET' }) 
            .then(configResponse => {
                if (!configResponse.ok) {
                    console.warn("Could not fetch current trade config, using defaults or placeholders. Status:", configResponse.status);
                    const defaults = { capital: "10000.00", trade_size_usd: "10.00", stop_loss_pct: "0.01", take_profit_pct: "0.02" };
                    if (capitalInput) capitalInput.value = defaults.capital;
                    if (tradeSizeInput) tradeSizeInput.value = defaults.trade_size_usd; 
                    if (stopLossInput) stopLossInput.value = defaults.stop_loss_pct;
                    if (takeProfitInput) takeProfitInput.value = defaults.take_profit_pct;
                    return Promise.reject(configResponse);
                }
                return configResponse.json();
            })
            .then(configData => {
                 if (configData) { 
                     if (capitalInput) capitalInput.value = configData.capital?.toFixed(2) ?? "10000.00";
                     if (tradeSizeInput) tradeSizeInput.value = configData.trade_size_usd?.toFixed(2) ?? "10.00";
                     if (stopLossInput) stopLossInput.value = configData.stop_loss_pct?.toFixed(3) ?? "0.01";
                     if (takeProfitInput) takeProfitInput.value = configData.take_profit_pct?.toFixed(3) ?? "0.02";
                 } else {
                     console.warn("Received empty config data, using placeholders.");
                     if (capitalInput) capitalInput.value = "10000.00";
                     if (tradeSizeInput) tradeSizeInput.value = "10.00";
                     if (stopLossInput) stopLossInput.value = "0.01";
                     if (takeProfitInput) takeProfitInput.value = "0.02";
                 }
            })
            .catch(error => {
                console.warn("Initialization UI: Error fetching or applying current trade config. Using placeholders:", error);
                if (capitalInput && !capitalInput.value) capitalInput.value = "10000.00";
                if (tradeSizeInput && !tradeSizeInput.value) tradeSizeInput.value = "10.00";
                if (stopLossInput && !stopLossInput.value) stopLossInput.value = "0.01";
                if (takeProfitInput && !takeProfitInput.value) takeProfitInput.value = "0.02";
            });
    }

    // --- Event Listeners ---
    if (startTradingBtn) {
        startTradingBtn.addEventListener('click', () => {
            fetch('/api/trading/start', { method: 'POST' })
                .then(response => {
                    if (!response.ok) {
                        console.error('Start trading returned error:', response.status, response.statusText);
                        return response.text().then(text => { throw new Error(text || 'Failed to send start command') });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Start trading response:', data);
                    alert(data.message || 'Trading script command sent.');
                    updateStatus(); 
                })
                .catch(error => {
                    console.error('Error starting trading:', error);
                    alert(`Failed to start trading: ${error.message}`);
                });
        });
    }
    if (stopTradingBtn) {
        stopTradingBtn.addEventListener('click', () => {
            fetch('/api/trading/stop', { method: 'POST' })
                .then(response => {
                    if (!response.ok) {
                        console.error('Stop trading returned error:', response.status, response.statusText);
                        return response.text().then(text => { throw new Error(text || 'Failed to send stop command') });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Stop trading response:', data);
                    alert(data.message || 'Trading script stop command sent.');
                    updateStatus(); 
                })
                .catch(error => {
                    console.error('Error stopping trading:', error);
                    alert(`Failed to stop trading: ${error.message}`);
                });
        });
    }
    if (generateLlmStrategiesBtn) {
        generateLlmStrategiesBtn.addEventListener('click', () => {
            fetch('/api/llm/generate', { method: 'POST' }) 
                .then(response => {
                    if (!response.ok) {
                        console.error('Generate LLM strategies returned error:', response.status, response.statusText);
                        return response.text().then(text => { throw new Error(text || 'Failed to send LLM generate command') });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Generate LLM strategies response:', data);
                    alert(data.message || 'LLM strategy generation command sent.');
                    updateStatus(); 
                })
                .catch(error => {
                    console.error('Error generating LLM strategies:', error);
                    alert(`Failed to generate LLM strategies: ${error.message}`);
                });
        });
    }
    if (saveTradingConfigBtn) {
        saveTradingConfigBtn.addEventListener('click', saveTradingConfig);
    }
    if (resetConfigBtn) {
        resetConfigBtn.addEventListener('click', () => {
            alert('Configuration reset to default values.');
            if (capitalInput) capitalInput.value = "10000.00";
            if (tradeSizeInput) tradeSizeInput.value = "10.00";
            if (stopLossInput) stopLossInput.value = "0.01";
            if (takeProfitInput) takeProfitInput.value = "0.02";
        });
    }

    // --- Initial Setup ---
    initializeUI();

    // --- Auto-refresh data periodically ---
    setInterval(updateStatus, 5000); 
    setInterval(updateTradeProgress, 60000); 
});

if (typeof Chart === 'undefined') {
    console.warn("Chart.js not found. Charts will not be rendered.");
}

function updateLogs() {
    fetch('/api/trading/logs')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching trading logs:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => {
            const tradingLogsPre = document.getElementById('tradingLogs');
            const tradingLogsTimestampSpan = document.getElementById('tradingLogsTimestamp');
            if (tradingLogsPre) tradingLogsPre.textContent = data.logs || 'No logs found.';
            if (tradingLogsTimestampSpan) {
                try {
                    tradingLogsTimestampSpan.textContent = data.last_updated ? `Last update: ${new Date(data.last_updated).toLocaleString()}` : '-';
                } catch (e) {
                    console.error("Error formatting log timestamp:", data.last_updated, e);
                    tradingLogsTimestampSpan.textContent = '-';
                }
            }
        })
        .catch(error => console.error('Error fetching trading logs:', error));

    fetch('/api/llm/logs')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching LLM logs:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => {
            const llmLogsPre = document.getElementById('llmLogs');
            if (llmLogsPre) llmLogsPre.textContent = data.logs || 'No LLM logs found.';
        })
        .catch(error => console.error('Error fetching LLM logs:', error));
}

function updateMarketData() {
    fetch('/api/market/prices')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching market prices:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => {
            const marketPricesContainer = document.getElementById('marketPricesContainer');
            if (marketPricesContainer) {
                marketPricesContainer.innerHTML = '<h4>Current Market Prices:</h4>';
                for (const symbol in data) {
                    marketPricesContainer.innerHTML += `<p><strong>${symbol}:</strong> $${data[symbol].toFixed(2)}</p>`;
                }
            }
        })
        .catch(error => console.error('Error fetching market prices:', error));

    fetch('/api/market/charts?symbol=BTC/USD&period=1h')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching BTC/USD chart data:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => renderChart('btcChart', data))
        .catch(error => console.error('Error fetching BTC/USD chart data:', error));
        
    fetch('/api/market/charts?symbol=ETH/USD&period=1h')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching ETH/USD chart data:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => renderChart('ethChart', data))
        .catch(error => console.error('Error fetching ETH/USD chart data:', error));

    fetch('/api/market/charts?symbol=SOL/USD&period=1h')
        .then(response => {
            if (!response.ok) {
                console.error('Error fetching SOL/USD chart data:', response.status, response.statusText);
                return Promise.reject(response);
            }
            return response.json();
        })
        .then(data => renderChart('solChart', data))
        .catch(error => console.error('Error fetching SOL/USD chart data:', error));
}

function renderChart(canvasId, chartData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    if (!ctx) {
        console.error(`Canvas element with id "${canvasId}" not found.`);
        return;
    }
    
    if (window.tradingCharts && window.tradingCharts[canvasId]) {
        window.tradingCharts[canvasId].destroy();
    } else if (window.tradingCharts) {
        window.tradingCharts[canvasId] = null; 
    } else {
        window.tradingCharts = {}; 
    }

    const timestamps = chartData.data.map(item => new Date(item.timestamp).toLocaleTimeString());
    const prices = chartData.data.map(item => item.price);

    const newChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: `${chartData.symbol} Price`,
                data: prices,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: false
                }
            },
            responsive: true,
            maintainAspectRatio: false
        }
    });
    window.tradingCharts[canvasId] = newChart; 
}
