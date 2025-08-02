import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.cgt_discount_days = 365  # 1 year for CGT discount eligibility
    
    def _format_currency(self, amount, include_symbol=True):
        """Format amount as currency with $ symbol and 2 decimal places."""
        formatted = f"{abs(amount):.2f}"
        if include_symbol:
            formatted = f"${formatted}"
        if amount < 0:
            formatted = f"({formatted})"
        return formatted
    
    def _format_date(self, date):
        """Format date in a consistent way."""
        return date.strftime("%d %b %Y")
    
    def _format_holding_period(self, days):
        """Format holding period in a readable way."""
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        remaining_days = remaining_days % 30
        
        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if months > 0:
            parts.append(f"{months}m")
        if remaining_days > 0 or not parts:  # include days if no years/months or if there are remaining days
            parts.append(f"{remaining_days}d")
        
        return " ".join(parts)

    def process_data(self, df):
        """Process the trading data and calculate capital gains/losses."""
        # Group by financial year
        df['Financial Year'] = df['Trade Date'].apply(self._get_financial_year)
        
        # Separate buy and sell transactions
        buys = df[df['Side'] == 'Buy'].copy()
        sells = df[df['Side'] == 'Sell'].copy()
        
        # Calculate cost base and capital proceeds
        results = self._match_trades(buys, sells)
        
        # Prepare summary and detailed breakdown
        summary = self._prepare_summary(results)
        details = self._prepare_details(results)
        
        return {
            'summary': summary,
            'details': details
        }
    
    def _get_financial_year(self, date):
        """Convert date to financial year string."""
        if date.month >= 7:
            return f"FY{date.year % 100}_{(date.year + 1) % 100}"
        return f"FY{(date.year - 1) % 100}_{date.year % 100}"
    
    def _match_trades(self, buys, sells):
        """Match buy and sell transactions using FIFO method."""
        results = []
        
        # Sort by date
        buys = buys.sort_values('Trade Date')
        sells = sells.sort_values('Trade Date')
        
        # Keep track of available shares for each symbol
        available_shares = {}
        
        # Initialize available shares from buy transactions
        for _, buy in buys.iterrows():
            symbol = buy['Symbol']
            if symbol not in available_shares:
                available_shares[symbol] = []
            
            available_shares[symbol].append({
                'date': buy['Trade Date'],
                'units': abs(buy['Units']),
                'value': abs(buy['Value']),
                'fees': buy['Fees'],
                'gst': buy['GST'],
                'rate': buy['AUD/USD rate'],
                'total_cost': (abs(buy['Value']) + buy['Fees'] + buy['GST']) * buy['AUD/USD rate']  # in AUD
            })
            
            logger.debug(f"Added {abs(buy['Units'])} units of {symbol} from {buy['Trade Date']}")
        
        for _, sell in sells.iterrows():
            symbol = sell['Symbol']
            units_to_sell = abs(sell['Units'])
            sell_date = sell['Trade Date']
            cost_base = 0
            matched_buys = []
            
            if symbol not in available_shares or not available_shares[symbol]:
                logger.warning(f"No available shares found for {symbol} at {sell_date}")
                continue
            
            logger.debug(f"\nProcessing sale of {units_to_sell} units of {symbol} on {sell_date}")
            
            # Match against available shares using FIFO
            remaining_to_sell = units_to_sell
            shares_list = available_shares[symbol]
            
            while remaining_to_sell > 0 and shares_list:
                oldest_parcel = shares_list[0]
                units_from_parcel = min(remaining_to_sell, oldest_parcel['units'])
                
                # Calculate portion of cost base for these units
                portion_of_total = units_from_parcel / oldest_parcel['units']
                cost_for_these_units = oldest_parcel['total_cost'] * portion_of_total
                
                matched_buys.append({
                    'date': oldest_parcel['date'],
                    'units': units_from_parcel,
                    'cost': cost_for_these_units
                })
                
                logger.debug(f"Matched {units_from_parcel} units from {oldest_parcel['date']}")
                logger.debug(f"Cost for these units: {self._format_currency(cost_for_these_units)} AUD")
                
                cost_base += cost_for_these_units
                remaining_to_sell -= units_from_parcel
                
                # Update or remove the parcel
                oldest_parcel['units'] -= units_from_parcel
                if oldest_parcel['units'] <= 0:
                    shares_list.pop(0)
                
            if remaining_to_sell > 0:
                logger.warning(f"Could not find enough shares to match sale: {remaining_to_sell} units short")
                continue
            
            if matched_buys:
                # Calculate proceeds in AUD
                sell_value = abs(sell['Value'])
                proceeds = (sell_value - sell['Fees'] - sell['GST']) * sell['AUD/USD rate']
                
                # Calculate individual gains/losses and check CGT discount eligibility for each parcel
                total_gain_loss = 0
                total_discounted_gain = 0
                total_undiscounted_gain = 0
                total_loss = 0
                
                for matched_buy in matched_buys:
                    # Calculate holding period for this parcel
                    holding_period = (sell['Trade Date'] - matched_buy['date']).days
                    portion_proceeds = (matched_buy['units'] / units_to_sell) * proceeds
                    parcel_gain_loss = portion_proceeds - matched_buy['cost']
                    
                    logger.debug(f"\nParcel analysis:")
                    logger.debug(f"Buy date: {self._format_date(matched_buy['date'])}")
                    logger.debug(f"Units: {matched_buy['units']}")
                    logger.debug(f"Holding period: {self._format_holding_period(holding_period)}")
                    logger.debug(f"Portion of proceeds: {self._format_currency(portion_proceeds)} AUD")
                    logger.debug(f"Cost base: {self._format_currency(matched_buy['cost'])} AUD")
                    logger.debug(f"Gain/Loss: {self._format_currency(parcel_gain_loss)} AUD")
                    
                    if parcel_gain_loss > 0:
                        if holding_period >= self.cgt_discount_days:
                            discounted_gain = parcel_gain_loss * 0.5
                            total_discounted_gain += discounted_gain
                            logger.debug(f"Eligible for CGT discount: {self._format_currency(parcel_gain_loss)} -> {self._format_currency(discounted_gain)}")
                        else:
                            total_undiscounted_gain += parcel_gain_loss
                            logger.debug(f"Not eligible for CGT discount: {self._format_currency(parcel_gain_loss)}")
                    else:
                        total_loss += parcel_gain_loss
                        logger.debug(f"Loss recorded: {self._format_currency(parcel_gain_loss)}")
                
                # Calculate total gain/loss
                total_gain_loss = total_discounted_gain + total_undiscounted_gain + total_loss
                
                # Debug information for overall trade
                logger.debug(f"\nOverall trade details for {sell['Symbol']}:")
                logger.debug(f"Units sold: {abs(sell['Units'])}")
                logger.debug(f"Sell value (USD): {self._format_currency(abs(sell['Value']))}")
                logger.debug(f"Sell fees (USD): {self._format_currency(sell['Fees'])}")
                logger.debug(f"Exchange rate: {sell['AUD/USD rate']:.4f}")
                logger.debug(f"Total proceeds (AUD): {self._format_currency(proceeds)}")
                logger.debug(f"Total cost base (AUD): {self._format_currency(sum(m['cost'] for m in matched_buys))}")
                logger.debug(f"Total gain/loss (AUD): {self._format_currency(total_gain_loss)}")
                logger.debug(f"Discounted gains (AUD): {self._format_currency(total_discounted_gain)}")
                logger.debug(f"Undiscounted gains (AUD): {self._format_currency(total_undiscounted_gain)}")
                logger.debug(f"Capital losses (AUD): {self._format_currency(abs(total_loss))}")
                
                # Format dates and holding periods for the results
                formatted_buy_dates = [self._format_date(m['date']) for m in matched_buys]
                formatted_holding_periods = [self._format_holding_period((sell['Trade Date'] - m['date']).days) for m in matched_buys]
                
                results.append({
                    'symbol': sell['Symbol'],
                    'buy_dates': formatted_buy_dates,
                    'sell_date': self._format_date(sell['Trade Date']),
                    'units': sell['Units'],
                    'cost_base': sum(m['cost'] for m in matched_buys),
                    'proceeds': proceeds,
                    'total_gain_loss': total_gain_loss,
                    'discounted_gain': total_discounted_gain,
                    'undiscounted_gain': total_undiscounted_gain,
                    'capital_loss': total_loss,
                    'financial_year': self._get_financial_year(sell['Trade Date']),
                    'holding_periods': formatted_holding_periods
                })
        
        return results
    
    def _prepare_summary(self, results):
        """Prepare summary of capital gains/losses by financial year."""
        summary = {}
        
        # Debug information
        logger.debug("Processing results for summary:")
        logger.debug(f"Number of trades to process: {len(results)}")
        
        for trade in results:
            fy = trade['financial_year']
            if fy not in summary:
                summary[fy] = {
                    'total_gains': 0.0,
                    'total_losses': 0.0,
                    'net_position': 0.0
                }
            
            # Calculate totals from the detailed breakdown
            discounted_gain = float(trade['discounted_gain'])
            undiscounted_gain = float(trade['undiscounted_gain'])
            capital_loss = float(trade['capital_loss'])
            total_gain_loss = float(trade['total_gain_loss'])
            
            logger.debug(f"\nProcessing trade for {trade['symbol']}:")
            logger.debug(f"Financial Year: {fy}")
            logger.debug(f"Total Gain/Loss: {self._format_currency(total_gain_loss)}")
            logger.debug(f"Discounted Gain: {self._format_currency(discounted_gain)}")
            logger.debug(f"Undiscounted Gain: {self._format_currency(undiscounted_gain)}")
            logger.debug(f"Capital Loss: {self._format_currency(abs(capital_loss))}")
            
            # Update summary with the total gains (both discounted and undiscounted)
            summary[fy]['total_gains'] += discounted_gain + undiscounted_gain
            summary[fy]['total_losses'] += abs(capital_loss)
            summary[fy]['net_position'] = summary[fy]['total_gains'] - summary[fy]['total_losses']
            logger.debug(f"Updated net position: {self._format_currency(summary[fy]['net_position'])}")
        
        # Convert summary to DataFrame and format currency columns
        df = pd.DataFrame(summary).T
        currency_columns = ['total_gains', 'total_losses', 'net_position']
        for col in currency_columns:
            df[col] = df[col].apply(lambda x: self._format_currency(x))
        return df
    
    def _prepare_details(self, results):
        """Prepare detailed breakdown of trades by stock."""
        df = pd.DataFrame(results)
        
        # Format currency columns
        currency_columns = ['cost_base', 'proceeds', 'total_gain_loss', 
                          'discounted_gain', 'undiscounted_gain', 'capital_loss']
        for col in currency_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: self._format_currency(x))
        
        return df
