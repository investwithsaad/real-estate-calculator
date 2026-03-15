import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Real Estate Investment Calculator",
    page_icon="🔢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #ffffff;
    }
    .stApp {
        background-color: #ffffff;
    }
    h1 {
        color: #1e3a5f;
        font-weight: 700;
    }
    h2, h3 {
        color: #2c5282;
    }
    .stButton>button {
        background-color: #1e3a5f;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2c5282;
    }
    .metric-card {
        background-color: #f7fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1e3a5f;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def calculate_mortgage_payment(loan_amount, annual_rate, years, amortization_type="Standard"):
    """Calculate monthly mortgage payment"""
    if loan_amount <= 0 or annual_rate <= 0:
        return 0
    
    if amortization_type == "Interest Only":
        return loan_amount * (annual_rate / 100 / 12)
    else:
        # Standard amortization
        monthly_rate = annual_rate / 100 / 12
        num_payments = years * 12
        if monthly_rate == 0:
            return loan_amount / num_payments
        payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                  ((1 + monthly_rate)**num_payments - 1)
        return payment


def calculate_loan_balance(loan_amount, annual_rate, years, year_num, amortization_type="Standard"):
    """Calculate remaining loan balance after a certain number of years"""
    if amortization_type == "Interest Only":
        return loan_amount  # Balance doesn't decrease with interest-only
    
    monthly_rate = annual_rate / 100 / 12
    num_payments = years * 12
    payments_made = year_num * 12
    
    if payments_made >= num_payments:
        return 0
    
    if monthly_rate == 0:
        return loan_amount - (loan_amount / num_payments * payments_made)
    
    # Calculate remaining balance using amortization formula
    payment = calculate_mortgage_payment(loan_amount, annual_rate, years, amortization_type)
    remaining_balance = loan_amount * (1 + monthly_rate)**payments_made - \
                       payment * (((1 + monthly_rate)**payments_made - 1) / monthly_rate)
    
    return max(0, remaining_balance)


def calculate_investment_metrics(inputs):
    """Perform all investment calculations"""
    results = {}
    
    # Basic calculations
    total_project_cost = inputs['purchase_price'] + inputs['closing_costs'] + inputs['rehab_budget']
    down_payment_amount = inputs['purchase_price'] * (inputs['down_payment_pct'] / 100)
    loan_amount = inputs.get('loan_amount', inputs['purchase_price'] - down_payment_amount)
    points_fees_amount = loan_amount * (inputs['points_fees_pct'] / 100)
    
    total_cash_invested = down_payment_amount + inputs['closing_costs'] + inputs['rehab_budget'] + points_fees_amount
    
    results['total_project_cost'] = total_project_cost
    results['down_payment_amount'] = down_payment_amount
    results['loan_amount'] = loan_amount
    results['points_fees_amount'] = points_fees_amount
    results['total_cash_invested'] = total_cash_invested
    
    # Mortgage calculations
    monthly_payment = calculate_mortgage_payment(
        loan_amount, 
        inputs['interest_rate'], 
        inputs['loan_term'],
        inputs.get('amortization_type', 'Standard')
    )
    annual_debt_service = monthly_payment * 12
    
    results['monthly_payment'] = monthly_payment
    results['annual_debt_service'] = annual_debt_service
    
    # Income calculations
    if inputs['property_type'] == 'Single Family':
        gross_scheduled_rent = inputs['monthly_rent'] * 12
    else:  # Multifamily
        total_monthly_rent = sum(inputs['unit_rents'])
        gross_scheduled_rent = total_monthly_rent * 12
    
    vacancy_loss = gross_scheduled_rent * (inputs['vacancy_rate'] / 100)
    other_annual_income = inputs['other_monthly_income'] * 12
    effective_gross_income = gross_scheduled_rent - vacancy_loss + other_annual_income
    
    results['gross_scheduled_rent'] = gross_scheduled_rent
    results['vacancy_loss'] = vacancy_loss
    results['effective_gross_income'] = effective_gross_income
    results['monthly_income'] = effective_gross_income / 12
    
    # Operating Expenses
    property_tax = inputs['property_tax_annual']
    insurance = inputs['insurance_annual']
    
    # Maintenance
    if inputs.get('maintenance_type') == 'Percentage of Rent':
        maintenance = gross_scheduled_rent * (inputs['maintenance_pct'] / 100)
    else:
        maintenance = inputs['maintenance_monthly'] * 12
    
    repairs_reserve = inputs['repairs_reserve_monthly'] * 12
    capex_reserve = inputs['capex_reserve_monthly'] * 12
    
    # Property management on collected rent (EGI - vacancy)
    collected_rent = gross_scheduled_rent - vacancy_loss
    property_management = collected_rent * (inputs['property_mgmt_pct'] / 100)
    
    utilities = inputs['utilities_monthly'] * 12
    hoa_fees = inputs['hoa_monthly'] * 12
    admin_costs = inputs['admin_annual']
    
    total_operating_expenses = (property_tax + insurance + maintenance + repairs_reserve + 
                               capex_reserve + property_management + utilities + hoa_fees + admin_costs)
    
    results['total_operating_expenses'] = total_operating_expenses
    results['monthly_operating_expenses'] = total_operating_expenses / 12
    
    # NOI and Cash Flow
    noi = effective_gross_income - total_operating_expenses
    annual_cash_flow_before_tax = noi - annual_debt_service
    monthly_cash_flow = annual_cash_flow_before_tax / 12
    
    results['noi'] = noi
    results['annual_cash_flow_before_tax'] = annual_cash_flow_before_tax
    results['monthly_cash_flow'] = monthly_cash_flow
    
    # Key Ratios
    cap_rate = (noi / inputs['purchase_price']) * 100 if inputs['purchase_price'] > 0 else 0
    cash_on_cash = (annual_cash_flow_before_tax / total_cash_invested) * 100 if total_cash_invested > 0 else 0
    
    results['cap_rate'] = cap_rate
    results['cash_on_cash'] = cash_on_cash
    
    # Depreciation and Tax Impact
    depreciable_basis = inputs['purchase_price'] * (inputs['building_value_pct'] / 100)
    annual_depreciation = depreciable_basis / inputs['depreciation_period']
    tax_savings = annual_depreciation * (inputs['tax_rate'] / 100)
    after_tax_cash_flow = annual_cash_flow_before_tax + tax_savings
    
    results['depreciable_basis'] = depreciable_basis
    results['annual_depreciation'] = annual_depreciation
    results['tax_savings'] = tax_savings
    results['after_tax_cash_flow'] = after_tax_cash_flow
    
    # Multi-year projections
    hold_period = inputs['hold_period']
    years_data = []
    
    for year in range(1, hold_period + 1):
        year_data = {'year': year}
        
        # Property value with appreciation
        property_value = inputs['purchase_price'] * (1 + inputs['appreciation_rate'] / 100) ** year
        year_data['property_value'] = property_value
        
        # Loan balance
        loan_balance = calculate_loan_balance(
            loan_amount, 
            inputs['interest_rate'], 
            inputs['loan_term'], 
            year,
            inputs.get('amortization_type', 'Standard')
        )
        year_data['loan_balance'] = loan_balance
        
        # Equity
        equity = property_value - loan_balance
        year_data['equity'] = equity
        
        # Cash flow with rent growth and expense inflation
        year_gsr = gross_scheduled_rent * (1 + inputs['rent_growth_rate'] / 100) ** year
        year_vacancy = year_gsr * (inputs['vacancy_rate'] / 100)
        year_egi = year_gsr - year_vacancy + other_annual_income
        
        year_expenses = total_operating_expenses * (1 + inputs['expense_inflation_rate'] / 100) ** year
        year_noi = year_egi - year_expenses
        year_cash_flow = year_noi - annual_debt_service
        year_data['cash_flow'] = year_cash_flow
        year_data['noi'] = year_noi
        
        years_data.append(year_data)
    
    results['years_projection'] = years_data
    
    # Sale analysis
    sale_year = inputs.get('sale_year', hold_period)
    sale_price = inputs['purchase_price'] * (1 + inputs['appreciation_rate'] / 100) ** sale_year
    selling_costs = sale_price * (inputs['selling_costs_pct'] / 100)
    remaining_loan_balance = calculate_loan_balance(
        loan_amount, 
        inputs['interest_rate'], 
        inputs['loan_term'], 
        sale_year,
        inputs.get('amortization_type', 'Standard')
    )
    net_sale_proceeds = sale_price - selling_costs - remaining_loan_balance
    
    results['sale_price'] = sale_price
    results['selling_costs'] = selling_costs
    results['remaining_loan_balance'] = remaining_loan_balance
    results['net_sale_proceeds'] = net_sale_proceeds
    
    # Total returns
    total_cash_flow = sum([y['cash_flow'] for y in years_data])
    total_profit = total_cash_flow + net_sale_proceeds - total_cash_invested
    total_roi = (total_profit / total_cash_invested) * 100 if total_cash_invested > 0 else 0
    equity_multiple = (total_cash_flow + net_sale_proceeds) / total_cash_invested if total_cash_invested > 0 else 0
    
    results['total_cash_flow'] = total_cash_flow
    results['total_profit'] = total_profit
    results['total_roi'] = total_roi
    results['equity_multiple'] = equity_multiple
    
    return results


def create_charts(results, hold_period):
    """Create visualization charts"""
    years_data = results['years_projection']
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Equity line
    fig.add_trace(go.Scatter(
        x=[y['year'] for y in years_data],
        y=[y['equity'] for y in years_data],
        mode='lines+markers',
        name='Equity',
        line=dict(color='#1e3a5f', width=3),
        marker=dict(size=8)
    ))
    
    # Cash flow bars
    fig.add_trace(go.Bar(
        x=[y['year'] for y in years_data],
        y=[y['cash_flow'] for y in years_data],
        name='Annual Cash Flow',
        marker_color='#4299e1',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Equity Growth and Cash Flow Projection',
        xaxis=dict(title='Year', dtick=1),
        yaxis=dict(
            title='Equity ($)',
            title_font=dict(color='#1e3a5f'),
            tickfont=dict(color='#1e3a5f'),
            tickformat='$,.0f'
        ),
        yaxis2=dict(
            title='Annual Cash Flow ($)',
            title_font=dict(color='#4299e1'),
            tickfont=dict(color='#4299e1'),
            overlaying='y',
            side='right',
            tickformat='$,.0f'
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial', size=12),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)'),
        height=500
    )
    
    return fig


def format_currency(amount):
    """Format number as currency"""
    return f"${amount:,.2f}"


def format_percentage(value):
    """Format number as percentage"""
    return f"{value:.2f}%"


def save_contact_info(name, email, phone, property_type):
    """Save contact information to a CSV file"""
    import os
    import csv
    from datetime import datetime
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    contacts_file = os.path.join(script_dir, "leads.csv")
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(contacts_file)
    
    try:
        with open(contacts_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                writer.writerow(['Timestamp', 'Name', 'Email', 'Phone', 'Property Interest', 'IP Address'])
            
            # Write contact data
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([timestamp, name, email, phone, property_type, 'N/A'])
        
        return True
    except Exception as e:
        st.error(f"Error saving contact: {e}")
        return False


def show_contact_gate():
    """Display the contact information collection form"""
    import os
    
    # Get logo paths
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    real_logo_path = os.path.join(script_dir, "real_logo.png")
    d2d_logo_path = os.path.join(script_dir, "real_d2d_logo.png")
    
    # Enhanced CSS for subtle, faded logos in corners
    st.markdown("""
        <style>
        .logo-container {
            display: flex;
            align-items: flex-start;
            padding: 1rem 0.5rem;
        }
        .logo-left {
            justify-content: flex-start;
        }
        .logo-right {
            justify-content: flex-end;
        }
        .logo-image {
            opacity: 0.5;
            transition: opacity 0.3s ease, transform 0.3s ease;
            cursor: pointer;
        }
        .logo-image:hover {
            opacity: 0.8;
            transform: scale(1.05);
        }
        .header-title {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header with corner-aligned logos - wider center column
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        st.markdown("<div class='logo-container logo-left'>", unsafe_allow_html=True)
        try:
            if os.path.exists(real_logo_path):
                st.markdown("""
                    <a href="https://www.real-broker.com" target="_blank" title="Visit Real Broker">
                """, unsafe_allow_html=True)
                st.image(real_logo_path, width=70)  # Much smaller, very faded
                st.markdown("</a>", unsafe_allow_html=True)
        except:
            pass
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class='header-title'>
                <div style='text-align: center;'>
                    <h1 style='margin: 0; padding: 0; font-size: 2.2rem; font-weight: 700; color: #1e3a5f; line-height: 1.2;'>
                        Real Estate Investment Calculator
                    </h1>
                    <p style='margin: 0.75rem 0 0 0; padding: 0; color: #718096; font-size: 1.05rem; font-weight: 400;'>
                        By <strong style='color: #2c5282;'>Saad Tai</strong> – Realtor
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='logo-container logo-right'>", unsafe_allow_html=True)
        try:
            if os.path.exists(d2d_logo_path):
                st.markdown("""
                    <a href="https://www.real-broker.com" target="_blank" title="Learn About Real Broker">
                """, unsafe_allow_html=True)
                st.image(d2d_logo_path, width=60)  # Much smaller, very faded
                st.markdown("</a>", unsafe_allow_html=True)
        except:
            pass
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 2rem 0 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    
    # Lead capture form
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0 1rem 0;'>
            <h2 style='color: #1e3a5f;'>Get Your FREE Investment Analysis</h2>
            <p style='color: #4a5568; font-size: 1.1rem;'>
                Enter your information below to access the calculator and receive a copy of your analysis.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Create centered form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("contact_form"):
            st.markdown("### Your Contact Information")
            
            full_name = st.text_input(
                "Full Name *",
                placeholder="John Smith",
                help="We'll use this to personalize your report"
            )
            
            email = st.text_input(
                "Email Address *",
                placeholder="john@example.com",
                help="We'll send your analysis report to this email"
            )
            
            phone = st.text_input(
                "Phone Number *",
                placeholder="(555) 123-4567",
                help="Optional: For follow-up on investment opportunities"
            )
            
            property_interest = st.selectbox(
                "What type of property are you interested in?",
                ["Single Family Residence", "Multifamily (2-4 units)", "Multifamily (5+ units)", 
                 "Commercial", "Just exploring options"]
            )
            
            st.markdown("---")
            
            # Privacy note
            st.markdown("""
                <p style='color: #718096; font-size: 0.9rem; text-align: center;'>
                    Your information is secure and will never be shared with third parties.<br>
                    By submitting, you agree to receive property investment insights from Saad Tai.
                </p>
            """, unsafe_allow_html=True)
            
            submit_button = st.form_submit_button("Access Calculator", use_container_width=True)
            
            if submit_button:
                # Validate inputs
                if not full_name or not email:
                    st.error("Please fill in all required fields (marked with *)")
                elif '@' not in email or '.' not in email:
                    st.error("Please enter a valid email address")
                else:
                    # Save contact information
                    if save_contact_info(full_name, email, phone, property_interest):
                        # Grant access
                        st.session_state.has_access = True
                        st.session_state.user_info = {
                            'name': full_name,
                            'email': email,
                            'phone': phone,
                            'property_interest': property_interest
                        }
                        st.success(f"Welcome, {full_name.split()[0]}! Loading your calculator...")
                        st.rerun()
                    else:
                        st.error("There was an issue processing your information. Please try again.")
    
    # Benefits section
    st.markdown("---")
    st.markdown("### What You'll Get:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            **Comprehensive Analysis**
            - Cap Rate & Cash-on-Cash Returns
            - 10-Year Projections
            - Tax Benefits Analysis
            - Sale Profit Estimates
        """)
    
    with col2:
        st.markdown("""
            **Professional Reports**
            - Downloadable Summary
            - Detailed Cash Flow Breakdown
            - Interactive Charts
            - Investment Recommendations
        """)
    
    with col3:
        st.markdown("""
            **Expert Guidance**
            - Personalized Follow-up
            - Market Insights
            - Deal Analysis Support
            - Investment Opportunities
        """)


def show_calculator():
    """Display the main calculator interface"""
    import os
    
    # Get logo paths
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    real_logo_path = os.path.join(script_dir, "real_logo.png")
    d2d_logo_path = os.path.join(script_dir, "real_d2d_logo.png")
    
    # Enhanced CSS for subtle, faded logos in corners
    st.markdown("""
        <style>
        .logo-container {
            display: flex;
            align-items: flex-start;
            padding: 1rem 0.5rem;
        }
        .logo-left {
            justify-content: flex-start;
        }
        .logo-right {
            justify-content: flex-end;
        }
        .logo-image {
            opacity: 0.5;
            transition: opacity 0.3s ease, transform 0.3s ease;
            cursor: pointer;
        }
        .logo-image:hover {
            opacity: 0.8;
            transform: scale(1.05);
        }
        .header-title {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header with corner-aligned logos - wider center column
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        st.markdown("<div class='logo-container logo-left'>", unsafe_allow_html=True)
        try:
            if os.path.exists(real_logo_path):
                # Much smaller, very faded, left corner
                st.markdown("""
                    <a href="https://www.real-broker.com" target="_blank" title="Visit Real Broker">
                """, unsafe_allow_html=True)
                st.image(real_logo_path, width=70)  # Reduced from 90 to 60
                st.markdown("</a>", unsafe_allow_html=True)
        except:
            pass
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class='header-title'>
                <div style='text-align: center;'>
                    <h1 style='margin: 0; padding: 0; font-size: 2.2rem; font-weight: 700; color: #1e3a5f; line-height: 1.2;'>
                        Real Estate Investment Calculator
                    </h1>
                    <p style='margin: 0.75rem 0 0 0; padding: 0; color: #718096; font-size: 1.05rem; font-weight: 400;'>
                        By <strong style='color: #2c5282;'>Saad Tai</strong> – Realtor
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='logo-container logo-right'>", unsafe_allow_html=True)
        try:
            if os.path.exists(d2d_logo_path):
                # Much smaller, very faded, right corner
                st.markdown("""
                    <a href="https://www.real-broker.com" target="_blank" title="Learn About Real Broker">
                """, unsafe_allow_html=True)
                st.image(d2d_logo_path, width=60)  # Reduced from 75 to 50
                st.markdown("</a>", unsafe_allow_html=True)
        except:
            pass
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 2rem 0 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    
    # Welcome message for logged-in user
    if 'user_info' in st.session_state and st.session_state.user_info:
        user_name = st.session_state.user_info.get('name', '').split()[0]
        st.info(f"Welcome back, {user_name}! Let's analyze your investment opportunity.")


def main():
    """Main application function"""
    
    # Initialize session state for access control
    if 'has_access' not in st.session_state:
        st.session_state.has_access = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    
    # If user hasn't provided contact info, show the gate
    if not st.session_state.has_access:
        show_contact_gate()
        return  # Don't show calculator until they provide info
    
    # If they have access, show the calculator
    show_calculator()
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Deal Inputs")
        
        # Property Type Selection
        property_type = st.radio(
            "Property Type",
            ["Single Family", "Multifamily"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # Property & Purchase Section
        with st.expander("Property & Purchase", expanded=True):
            purchase_price = st.number_input(
                "Purchase Price ($)",
                min_value=0.0,
                value=300000.0,
                step=10000.0,
                help="Total property purchase price"
            )
            
            closing_costs = st.number_input(
                "Closing Costs ($)",
                min_value=0.0,
                value=9000.0,
                step=1000.0,
                help="Total closing costs"
            )
            
            rehab_budget = st.number_input(
                "Rehab / Renovation Budget ($)",
                min_value=0.0,
                value=15000.0,
                step=5000.0,
                help="Budget for repairs and renovations"
            )
            
            st.info(f"**Total Project Cost:** {format_currency(purchase_price + closing_costs + rehab_budget)}")
            
            acquisition_date = st.date_input(
                "Acquisition Date (Optional)",
                value=datetime.now()
            )
            
            col1, col2 = st.columns(2)
            with col1:
                land_value_pct = st.number_input(
                    "Land Value %",
                    min_value=0.0,
                    max_value=100.0,
                    value=20.0,
                    step=5.0
                )
            with col2:
                building_value_pct = st.number_input(
                    "Building Value %",
                    min_value=0.0,
                    max_value=100.0,
                    value=80.0,
                    step=5.0
                )
        
        # Financing Section
        with st.expander("Financing", expanded=True):
            down_payment_pct = st.slider(
                "Down Payment %",
                min_value=0,
                max_value=100,
                value=25,
                step=5
            )
            
            down_payment_amount = purchase_price * (down_payment_pct / 100)
            st.info(f"**Down Payment Amount:** {format_currency(down_payment_amount)}")
            
            default_loan = purchase_price - down_payment_amount
            loan_amount = st.number_input(
                "Loan Amount ($)",
                min_value=0.0,
                max_value=10000000.0,
                value=float(default_loan),
                step=10000.0,
                help="Override calculated loan amount if needed"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                loan_term = st.number_input(
                    "Loan Term (years)",
                    min_value=1,
                    max_value=40,
                    value=30,
                    step=5
                )
            with col2:
                interest_rate = st.number_input(
                    "Interest Rate (%)",
                    min_value=0.0,
                    max_value=20.0,
                    value=6.5,
                    step=0.25,
                    format="%.2f"
                )
            
            points_fees_pct = st.number_input(
                "Points / Loan Fees (%)",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.5,
                format="%.2f"
            )
            
            amortization_type = st.selectbox(
                "Amortization Type",
                ["Standard (Principal + Interest)", "Interest Only"]
            )
            
            st.markdown("**Optional Refinance:**")
            col1, col2 = st.columns(2)
            with col1:
                refi_year = st.number_input(
                    "Refinance Year",
                    min_value=0,
                    max_value=30,
                    value=0,
                    step=1,
                    help="Leave 0 for no refinance"
                )
            with col2:
                refi_rate = st.number_input(
                    "Refi Rate (%)",
                    min_value=0.0,
                    value=5.5,
                    step=0.25,
                    format="%.2f"
                )
        
        # Income Section
        with st.expander("Income", expanded=True):
            if property_type == "Single Family":
                monthly_rent = st.number_input(
                    "Monthly Rent ($)",
                    min_value=0.0,
                    value=2500.0,
                    step=100.0
                )
                unit_rents = [monthly_rent]
            else:  # Multifamily
                num_units = st.number_input(
                    "Number of Units",
                    min_value=1,
                    max_value=10,
                    value=4,
                    step=1
                )
                
                unit_rents = []
                st.markdown("**Unit Rents:**")
                cols = st.columns(2)
                for i in range(num_units):
                    with cols[i % 2]:
                        rent = st.number_input(
                            f"Unit {i+1} Rent ($)",
                            min_value=0.0,
                            value=1500.0,
                            step=50.0,
                            key=f"unit_{i}"
                        )
                        unit_rents.append(rent)
            
            other_monthly_income = st.number_input(
                "Other Monthly Income ($)",
                min_value=0.0,
                value=100.0,
                step=50.0,
                help="Parking, laundry, fees, etc."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                vacancy_rate = st.number_input(
                    "Vacancy Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=5.0,
                    step=1.0,
                    format="%.1f"
                )
            with col2:
                rent_growth_rate = st.number_input(
                    "Rent Growth Rate (%/year)",
                    min_value=0.0,
                    max_value=20.0,
                    value=3.0,
                    step=0.5,
                    format="%.1f"
                )
        
        # Operating Expenses Section
        with st.expander("Operating Expenses", expanded=False):
            property_tax_annual = st.number_input(
                "Property Taxes ($ per year)",
                min_value=0.0,
                value=4500.0,
                step=500.0
            )
            
            insurance_annual = st.number_input(
                "Insurance ($ per year)",
                min_value=0.0,
                value=1500.0,
                step=100.0
            )
            
            maintenance_type = st.radio(
                "Maintenance Input Type",
                ["Percentage of Rent", "Fixed Monthly"],
                horizontal=True
            )
            
            if maintenance_type == "Percentage of Rent":
                maintenance_pct = st.number_input(
                    "Maintenance (% of rent)",
                    min_value=0.0,
                    max_value=50.0,
                    value=5.0,
                    step=1.0,
                    format="%.1f"
                )
                maintenance_monthly = 0.0
            else:
                maintenance_monthly = st.number_input(
                    "Maintenance ($ per month)",
                    min_value=0.0,
                    value=150.0,
                    step=50.0
                )
                maintenance_pct = 0.0
            
            repairs_reserve_monthly = st.number_input(
                "Repairs & Turnover Reserve ($/month)",
                min_value=0.0,
                value=100.0,
                step=25.0
            )
            
            capex_reserve_monthly = st.number_input(
                "CapEx Reserve ($/month)",
                min_value=0.0,
                value=150.0,
                step=25.0
            )
            
            property_mgmt_pct = st.number_input(
                "Property Management (% of collected rent)",
                min_value=0.0,
                max_value=20.0,
                value=8.0,
                step=1.0,
                format="%.1f"
            )
            
            utilities_monthly = st.number_input(
                "Utilities - Owner Paid ($/month)",
                min_value=0.0,
                value=0.0,
                step=50.0
            )
            
            hoa_monthly = st.number_input(
                "HOA Fees ($/month)",
                min_value=0.0,
                value=0.0,
                step=50.0
            )
            
            admin_annual = st.number_input(
                "Admin / Legal / Accounting ($/year)",
                min_value=0.0,
                value=500.0,
                step=100.0
            )
        
        # Tax & Market Assumptions Section
        with st.expander("Tax & Market Assumptions", expanded=False):
            tax_rate = st.number_input(
                "Marginal Tax Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=25.0,
                step=1.0,
                format="%.1f"
            )
            
            depreciation_period = st.number_input(
                "Depreciation Period (years)",
                min_value=1.0,
                max_value=50.0,
                value=27.5,
                step=0.5,
                format="%.1f"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                appreciation_rate = st.number_input(
                    "Appreciation Rate (%/year)",
                    min_value=0.0,
                    max_value=20.0,
                    value=3.0,
                    step=0.5,
                    format="%.1f"
                )
            with col2:
                expense_inflation_rate = st.number_input(
                    "Expense Inflation (%/year)",
                    min_value=0.0,
                    max_value=20.0,
                    value=2.0,
                    step=0.5,
                    format="%.1f"
                )
            
            hold_period = st.number_input(
                "Planned Hold Period (years)",
                min_value=1,
                max_value=30,
                value=10,
                step=1
            )
            
            sale_year = st.number_input(
                "Planned Sale Year",
                min_value=1,
                max_value=30,
                value=int(hold_period),
                step=1
            )
            
            selling_costs_pct = st.number_input(
                "Selling Costs (% of sale price)",
                min_value=0.0,
                max_value=20.0,
                value=7.0,
                step=0.5,
                format="%.1f"
            )
        
        # Investor Targets Section
        with st.expander("Investor Targets", expanded=False):
            target_coc = st.number_input(
                "Target Cash-on-Cash Return (%)",
                min_value=0.0,
                value=8.0,
                step=1.0,
                format="%.1f"
            )
            
            target_roi = st.number_input(
                "Target Total ROI (%)",
                min_value=0.0,
                value=100.0,
                step=10.0,
                format="%.1f"
            )
    
    # Compile all inputs
    inputs = {
        'property_type': property_type,
        'purchase_price': purchase_price,
        'closing_costs': closing_costs,
        'rehab_budget': rehab_budget,
        'land_value_pct': land_value_pct,
        'building_value_pct': building_value_pct,
        'down_payment_pct': down_payment_pct,
        'loan_amount': loan_amount,
        'loan_term': loan_term,
        'interest_rate': interest_rate,
        'points_fees_pct': points_fees_pct,
        'amortization_type': amortization_type,
        'monthly_rent': unit_rents[0] if property_type == "Single Family" else 0,
        'unit_rents': unit_rents,
        'other_monthly_income': other_monthly_income,
        'vacancy_rate': vacancy_rate,
        'rent_growth_rate': rent_growth_rate,
        'property_tax_annual': property_tax_annual,
        'insurance_annual': insurance_annual,
        'maintenance_type': maintenance_type,
        'maintenance_pct': maintenance_pct,
        'maintenance_monthly': maintenance_monthly,
        'repairs_reserve_monthly': repairs_reserve_monthly,
        'capex_reserve_monthly': capex_reserve_monthly,
        'property_mgmt_pct': property_mgmt_pct,
        'utilities_monthly': utilities_monthly,
        'hoa_monthly': hoa_monthly,
        'admin_annual': admin_annual,
        'tax_rate': tax_rate,
        'depreciation_period': depreciation_period,
        'appreciation_rate': appreciation_rate,
        'expense_inflation_rate': expense_inflation_rate,
        'hold_period': hold_period,
        'sale_year': sale_year,
        'selling_costs_pct': selling_costs_pct,
        'target_coc': target_coc,
        'target_roi': target_roi
    }
    
    # Calculate results
    results = calculate_investment_metrics(inputs)
    
    # Main content area
    st.header("Investment Analysis Results")
    
    # Key Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Cap Rate",
            value=format_percentage(results['cap_rate']),
            help="Net Operating Income / Purchase Price"
        )
    
    with col2:
        coc_delta = results['cash_on_cash'] - inputs['target_coc']
        st.metric(
            label="Cash-on-Cash Return",
            value=format_percentage(results['cash_on_cash']),
            delta=format_percentage(coc_delta),
            help=f"Target: {format_percentage(inputs['target_coc'])}"
        )
    
    with col3:
        st.metric(
            label="Monthly Cash Flow",
            value=format_currency(results['monthly_cash_flow']),
            help="After debt service, before taxes"
        )
    
    with col4:
        roi_delta = results['total_roi'] - inputs['target_roi']
        st.metric(
            label="Total ROI",
            value=format_percentage(results['total_roi']),
            delta=format_percentage(roi_delta),
            help=f"Target: {format_percentage(inputs['target_roi'])}"
        )
    
    st.markdown("---")
    
    # Detailed Results in Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Summary", 
        "Cash Flow Analysis", 
        "Projections & Charts",
        "Sale Analysis"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Investment Summary")
            st.write(f"**Purchase Price:** {format_currency(inputs['purchase_price'])}")
            st.write(f"**Total Project Cost:** {format_currency(results['total_project_cost'])}")
            st.write(f"**Total Cash Invested:** {format_currency(results['total_cash_invested'])}")
            st.write(f"**Loan Amount:** {format_currency(results['loan_amount'])}")
            st.write(f"**Monthly Payment:** {format_currency(results['monthly_payment'])}")
            
            st.markdown("---")
            
            st.subheader("Income")
            st.write(f"**Gross Scheduled Rent:** {format_currency(results['gross_scheduled_rent'])} / year")
            st.write(f"**Vacancy Loss:** {format_currency(results['vacancy_loss'])} / year")
            st.write(f"**Effective Gross Income:** {format_currency(results['effective_gross_income'])} / year")
            st.write(f"**Monthly Income:** {format_currency(results['monthly_income'])}")
        
        with col2:
            st.subheader("Operating Performance")
            st.write(f"**Operating Expenses:** {format_currency(results['total_operating_expenses'])} / year")
            st.write(f"**Net Operating Income (NOI):** {format_currency(results['noi'])} / year")
            st.write(f"**Annual Debt Service:** {format_currency(results['annual_debt_service'])}")
            st.write(f"**Annual Cash Flow (Before Tax):** {format_currency(results['annual_cash_flow_before_tax'])}")
            
            st.markdown("---")
            
            st.subheader("Tax Benefits")
            st.write(f"**Depreciable Basis:** {format_currency(results['depreciable_basis'])}")
            st.write(f"**Annual Depreciation:** {format_currency(results['annual_depreciation'])}")
            st.write(f"**Tax Savings from Depreciation:** {format_currency(results['tax_savings'])}")
            st.write(f"**After-Tax Cash Flow:** {format_currency(results['after_tax_cash_flow'])} / year")
    
    with tab2:
        st.subheader("Year 1 Cash Flow Breakdown")
        
        # Create a detailed cash flow table
        cash_flow_data = {
            'Category': [
                'Gross Scheduled Rent',
                'Less: Vacancy',
                'Plus: Other Income',
                'Effective Gross Income',
                '',
                'Operating Expenses',
                'Net Operating Income (NOI)',
                '',
                'Annual Debt Service',
                'Cash Flow Before Tax',
                'Tax Savings (Depreciation)',
                'Cash Flow After Tax'
            ],
            'Annual Amount': [
                format_currency(results['gross_scheduled_rent']),
                f"({format_currency(results['vacancy_loss'])})",
                format_currency(inputs['other_monthly_income'] * 12),
                format_currency(results['effective_gross_income']),
                '',
                f"({format_currency(results['total_operating_expenses'])})",
                format_currency(results['noi']),
                '',
                f"({format_currency(results['annual_debt_service'])})",
                format_currency(results['annual_cash_flow_before_tax']),
                format_currency(results['tax_savings']),
                format_currency(results['after_tax_cash_flow'])
            ]
        }
        
        df_cash_flow = pd.DataFrame(cash_flow_data)
        st.dataframe(df_cash_flow, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Operating Expense Breakdown")
            expense_breakdown = {
                'Expense Type': [
                    'Property Taxes',
                    'Insurance',
                    'Maintenance',
                    'Repairs & Turnover',
                    'CapEx Reserve',
                    'Property Management',
                    'Utilities',
                    'HOA Fees',
                    'Admin/Legal'
                ],
                'Annual Cost': [
                    format_currency(inputs['property_tax_annual']),
                    format_currency(inputs['insurance_annual']),
                    format_currency(results['gross_scheduled_rent'] * (inputs['maintenance_pct'] / 100) if maintenance_type == 'Percentage of Rent' else inputs['maintenance_monthly'] * 12),
                    format_currency(inputs['repairs_reserve_monthly'] * 12),
                    format_currency(inputs['capex_reserve_monthly'] * 12),
                    format_currency(results['gross_scheduled_rent'] * (1 - inputs['vacancy_rate']/100) * (inputs['property_mgmt_pct'] / 100)),
                    format_currency(inputs['utilities_monthly'] * 12),
                    format_currency(inputs['hoa_monthly'] * 12),
                    format_currency(inputs['admin_annual'])
                ]
            }
            df_expenses = pd.DataFrame(expense_breakdown)
            st.dataframe(df_expenses, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Key Ratios")
            st.metric("Operating Expense Ratio", 
                     format_percentage((results['total_operating_expenses'] / results['effective_gross_income']) * 100))
            st.metric("Debt Service Coverage Ratio (DSCR)", 
                     f"{(results['noi'] / results['annual_debt_service']):.2f}x")
            st.metric("Break-even Occupancy", 
                     format_percentage(((results['total_operating_expenses'] + results['annual_debt_service']) / results['gross_scheduled_rent']) * 100))
    
    with tab3:
        st.subheader("Multi-Year Projections")
        
        # Display the chart
        fig = create_charts(results, inputs['hold_period'])
        st.plotly_chart(fig, use_container_width=True)
        
        # Year-by-year table
        st.subheader("Year-by-Year Details")
        
        years_df_data = {
            'Year': [],
            'Property Value': [],
            'Loan Balance': [],
            'Equity': [],
            'NOI': [],
            'Cash Flow': []
        }
        
        for year_data in results['years_projection']:
            years_df_data['Year'].append(year_data['year'])
            years_df_data['Property Value'].append(format_currency(year_data['property_value']))
            years_df_data['Loan Balance'].append(format_currency(year_data['loan_balance']))
            years_df_data['Equity'].append(format_currency(year_data['equity']))
            years_df_data['NOI'].append(format_currency(year_data['noi']))
            years_df_data['Cash Flow'].append(format_currency(year_data['cash_flow']))
        
        df_years = pd.DataFrame(years_df_data)
        st.dataframe(df_years, use_container_width=True, hide_index=True)
        
        # Summary statement
        st.info(f"""
        **Investment Summary:** Over {inputs['hold_period']} years, this property is projected to produce 
        **{format_currency(results['total_cash_flow'])}** in total cash flow and reach an estimated value of 
        **{format_currency(results['years_projection'][-1]['property_value'])}**, for a total ROI of 
        **{format_percentage(results['total_roi'])}** and equity multiple of **{results['equity_multiple']:.2f}x**.
        """)
    
    with tab4:
        st.subheader(f"Sale Analysis (Year {inputs['sale_year']})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Projected Sale Price:** {format_currency(results['sale_price'])}")
            st.write(f"**Less: Selling Costs ({inputs['selling_costs_pct']}%):** {format_currency(results['selling_costs'])}")
            st.write(f"**Less: Remaining Loan Balance:** {format_currency(results['remaining_loan_balance'])}")
            st.write(f"**Net Sale Proceeds:** {format_currency(results['net_sale_proceeds'])}")
        
        with col2:
            st.write(f"**Total Cash Flow (All Years):** {format_currency(results['total_cash_flow'])}")
            st.write(f"**Net Sale Proceeds:** {format_currency(results['net_sale_proceeds'])}")
            st.write(f"**Less: Initial Investment:** {format_currency(results['total_cash_invested'])}")
            st.write(f"**Total Profit:** {format_currency(results['total_profit'])}")
            
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total ROI", format_percentage(results['total_roi']))
        with col2:
            st.metric("Equity Multiple", f"{results['equity_multiple']:.2f}x")
        with col3:
            annualized_return = ((results['equity_multiple']) ** (1/inputs['sale_year']) - 1) * 100
            st.metric("Annualized Return", format_percentage(annualized_return))
    
    st.markdown("---")
    
    # Lead Capture Section
    st.header("Save Your Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        user_email = st.text_input(
            "Enter your email to save or export this analysis",
            placeholder="your.email@example.com"
        )
        
        if user_email and '@' in user_email:
            st.success("We'll send you a copy of this analysis.")
            # Placeholder for future email integration
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        generate_report = st.button("Generate Investor Summary", use_container_width=True)
    
    # Contact CTA
    st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; 
                    border-radius: 10px; 
                    text-align: center; 
                    margin: 1.5rem 0;'>
            <p style='color: white; font-size: 1.1rem; margin: 0 0 0.5rem 0; font-weight: 500;'>
                Want to discuss this deal?
            </p>
            <p style='color: white; font-size: 1.4rem; margin: 0.5rem 0; font-weight: 700;'>
                <a href='tel:+15183489535' style='color: white; text-decoration: none;'>
                    (518) 348-9535
                </a>
            </p>
            <p style='color: rgba(255,255,255,0.9); font-size: 0.95rem; margin: 0.5rem 0 0 0;'>
                Call or text me anytime - Let's find your next investment!
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Generate Investor Summary
    if generate_report:
        st.markdown("---")
        st.subheader("Investor Summary Report")
        
        summary_text = f"""
### Investment Property Analysis
**Generated:** {datetime.now().strftime("%B %d, %Y")}
**Property Type:** {inputs['property_type']}

---

#### Key Investment Details

**Purchase Information:**
- Purchase Price: {format_currency(inputs['purchase_price'])}
- Closing Costs: {format_currency(inputs['closing_costs'])}
- Rehab Budget: {format_currency(inputs['rehab_budget'])}
- **Total Project Cost: {format_currency(results['total_project_cost'])}**

**Financing:**
- Down Payment: {format_percentage(inputs['down_payment_pct'])} ({format_currency(results['down_payment_amount'])})
- Loan Amount: {format_currency(results['loan_amount'])}
- Interest Rate: {format_percentage(inputs['interest_rate'])}
- Loan Term: {inputs['loan_term']} years
- Monthly Payment: {format_currency(results['monthly_payment'])}

**Income (Year 1):**
- Gross Scheduled Rent: {format_currency(results['gross_scheduled_rent'])} / year
- Vacancy Loss: {format_currency(results['vacancy_loss'])} / year
- Effective Gross Income: {format_currency(results['effective_gross_income'])} / year

---

#### Performance Metrics

**Operating Performance:**
- Net Operating Income (NOI): {format_currency(results['noi'])} / year
- Operating Expenses: {format_currency(results['total_operating_expenses'])} / year
- Annual Cash Flow (Before Tax): {format_currency(results['annual_cash_flow_before_tax'])}
- Annual Cash Flow (After Tax): {format_currency(results['after_tax_cash_flow'])}

**Key Ratios:**
- Cap Rate: {format_percentage(results['cap_rate'])}
- Cash-on-Cash Return: {format_percentage(results['cash_on_cash'])}
- Debt Service Coverage Ratio: {(results['noi'] / results['annual_debt_service']):.2f}x

---

#### Long-Term Projections ({inputs['hold_period']} Years)

**Property Appreciation:**
- Current Value: {format_currency(inputs['purchase_price'])}
- Projected Value (Year {inputs['hold_period']}): {format_currency(results['years_projection'][-1]['property_value'])}
- Total Appreciation: {format_currency(results['years_projection'][-1]['property_value'] - inputs['purchase_price'])}

**Equity Growth:**
- Initial Equity: {format_currency(results['down_payment_amount'])}
- Projected Equity (Year {inputs['hold_period']}): {format_currency(results['years_projection'][-1]['equity'])}

**Sale Analysis (Year {inputs['sale_year']}):**
- Sale Price: {format_currency(results['sale_price'])}
- Selling Costs: {format_currency(results['selling_costs'])}
- Net Sale Proceeds: {format_currency(results['net_sale_proceeds'])}

---

#### Total Return Summary

- Total Cash Invested: {format_currency(results['total_cash_invested'])}
- Total Cash Flow (All Years): {format_currency(results['total_cash_flow'])}
- Net Sale Proceeds: {format_currency(results['net_sale_proceeds'])}
- **Total Profit: {format_currency(results['total_profit'])}**
- **Total ROI: {format_percentage(results['total_roi'])}**
- **Equity Multiple: {results['equity_multiple']:.2f}x**

---

#### Investment Recommendation

"""
        
        # Add recommendation based on targets
        if results['cash_on_cash'] >= inputs['target_coc'] and results['total_roi'] >= inputs['target_roi']:
            summary_text += "**This investment MEETS your target criteria.** "
            summary_text += f"The Cash-on-Cash return of {format_percentage(results['cash_on_cash'])} exceeds your target of {format_percentage(inputs['target_coc'])}, "
            summary_text += f"and the Total ROI of {format_percentage(results['total_roi'])} exceeds your target of {format_percentage(inputs['target_roi'])}."
        elif results['cash_on_cash'] >= inputs['target_coc']:
            summary_text += "**This investment PARTIALLY MEETS your criteria.** "
            summary_text += f"While the Cash-on-Cash return of {format_percentage(results['cash_on_cash'])} meets your target, "
            summary_text += f"the Total ROI of {format_percentage(results['total_roi'])} falls short of your {format_percentage(inputs['target_roi'])} target."
        elif results['total_roi'] >= inputs['target_roi']:
            summary_text += "**This investment PARTIALLY MEETS your criteria.** "
            summary_text += f"While the Total ROI of {format_percentage(results['total_roi'])} meets your target, "
            summary_text += f"the Cash-on-Cash return of {format_percentage(results['cash_on_cash'])} falls short of your {format_percentage(inputs['target_coc'])} target."
        else:
            summary_text += "**This investment DOES NOT MEET your target criteria.** "
            summary_text += f"Both the Cash-on-Cash return ({format_percentage(results['cash_on_cash'])}) and Total ROI ({format_percentage(results['total_roi'])}) "
            summary_text += f"fall short of your targets."
        
        summary_text += "---\n\n"
        summary_text += "*This analysis is for informational purposes only and should not be considered financial advice. "
        summary_text += "Please consult with qualified professionals before making investment decisions.*\n\n"
        summary_text += f"**Prepared by Saad Tai – Realtor**\n\n"
        summary_text += f"**Contact:** (518) 348-9535 | Call or Text Anytime\n"
        summary_text += f"Ready to discuss your investment opportunity? Let's talk!"
        
        st.markdown(summary_text)
        
        # Download button for the report
        st.download_button(
            label="Download Summary as Text",
            data=summary_text,
            file_name=f"investment_summary_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #718096; padding: 2rem 0 1rem 0;'>
            <p style='font-size: 1.1rem; margin-bottom: 1rem; color: #2c5282;'>
                <strong>Ready to discuss your investment opportunity?</strong>
            </p>
            <p style='font-size: 1.3rem; margin: 0.5rem 0 1.5rem 0;'>
                <strong style='color: #1e3a5f;'>Call or Text: 
                <a href='tel:+15183489535' style='color: #1e3a5f; text-decoration: none; border-bottom: 2px solid #4299e1;'>
                    (518) 348-9535
                </a>
                </strong>
            </p>
            <p style='color: #718096; font-size: 0.95rem; margin-top: 1.5rem;'>
                Created by <strong>Saad Tai</strong> – Realtor
            </p>
            <p style='font-size: 0.85rem; color: #a0aec0;'>
                For questions or to discuss investment opportunities, reach out anytime.
            </p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
