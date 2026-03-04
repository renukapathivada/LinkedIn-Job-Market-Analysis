import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
import random


skills_map = {
    'Data Analyst/BI': ['SQL', 'Excel', 'Tableau', 'Power BI', 'Python', 'Statistics'],
    'Data Scientist/ML': ['Python', 'Machine Learning', 'SQL', 'TensorFlow', 'PyTorch', 'Deep Learning', 'R'],
    'Data Engineer': ['SQL', 'Python', 'Spark', 'Kafka', 'ETL', 'AWS', 'Azure'],
    'Software Developer': ['Java', 'Python', 'C++', 'JavaScript', 'Spring', 'React'],
    'Solution Architect': ['Cloud', 'AWS', 'Azure', 'GCP', 'Design Patterns', 'System Integration']
}
salary_bases_lacs = { 
    'Data Analyst/BI': 6.0, 'Data Scientist/ML': 9.0, 'Data Engineer': 8.5, 
    'Software Developer': 7.5, 'Solution Architect': 12.0
}
experience_multipliers = {
    'Entry level': 0.8, 'Mid-Senior level': 1.5, 'Director': 2.5, 
    'Executive': 3.0, 'Not Applicable': 1.0 
}

def normalize_job_title(title):
    title = str(title).lower()
    title = re.sub(r'\(.*?\)|senior|sr|lead|jr|junior|staff|principal|manager|associate|entry level|mid-senior level', '', title).strip()

    if 'data scientist' in title or 'ai/ml' in title or 'artificial intelligence' in title or 'machine learning' in title:
        return 'Data Scientist/ML'
    elif 'data analyst' in title or 'business analyst' in title or 'bi analyst' in title or 'reporting analyst' in title:
        return 'Data Analyst/BI'
    elif 'data engineer' in title or 'etl' in title or 'data warehousing' in title or 'pipeline' in title:
        return 'Data Engineer'
    elif 'software developer' in title or 'software engineer' in title:
        return 'Software Developer'
    elif 'solution architect' in title or 'cloud architect' in title:
        return 'Solution Architect'
    else:
        return 'Other'

def impute_skills(job_title):
    skill_list = skills_map.get(job_title, [])
    if not skill_list: return ""
    k = random.randint(2, len(skill_list)) if len(skill_list) >= 2 else len(skill_list)
    return ", ".join(random.sample(skill_list, k=k))

def impute_salary(row):
    base = salary_bases_lacs.get(row['Normalized_Job_Title'], 5.0) * 100000 
    multiplier = experience_multipliers.get(row['Experience_Level'], 1.0)
    
    year_adjustment = (row['Year'] - 2022) * 0.10 if row['Year'] > 2022 else 0
    
    base_salary = base * multiplier * (1 + year_adjustment)
    
    noise = np.random.uniform(0.85, 1.15)
    final_salary = round(base_salary * noise, -3) 
    
    return int(final_salary)

@st.cache_data
def process_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None

    # Determine file type and read data
    file_type = uploaded_file.name.split('.')[-1]
    # Use io.BytesIO for robust reading
    if file_type in ['xlsx', 'xls']:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    else: # Assume CSV
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file) 

    # --- Data Cleaning and Normalization ---
    df.columns = [col.lower().strip() for col in df.columns]
    df = df.rename(columns={
        'date': 'Date', 'job_title': 'Job_Title', 'seniority_level': 'Experience_Level', 'industry': 'Industry', 'company_name': 'Company_Name'
    })
    
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip().str.replace('\n', '', regex=False)
        
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df['Year'] = df['Date'].dt.year

    # --- Feature Engineering (Imputation) ---
    df['Normalized_Job_Title'] = df['Job_Title'].apply(normalize_job_title)
    df = df[df['Normalized_Job_Title'] != 'Other'].copy()
    
    df['Required_Skills'] = df['Normalized_Job_Title'].apply(impute_skills)
    df['Salary'] = df.apply(impute_salary, axis=1)
    
    return df

# --- Streamlit UI Setup ---

st.set_page_config(
    page_title="LinkedIn Job Market Trend Analysis (Enhanced)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Live Job Market Trend Analysis 📈")
st.markdown("### Upload Your LinkedIn Job Data to View Dynamic Trends (2022-2023)")

uploaded_file = st.file_uploader(
    "Upload Your LinkedIn Job Posts XLSX/CSV File", 
    type=['xlsx', 'csv']
)

if uploaded_file is None:
    st.info("Please upload your job posts file to begin the analysis.")
    st.stop()

# --- Process and Filter Data ---
with st.spinner('Processing and analyzing data...'):
    df = process_uploaded_file(uploaded_file)

# Global aesthetics settings
COLOR_PALETTE = px.colors.qualitative.Plotly
TEMPLATE = "plotly_dark" 

if df is not None:
    st.sidebar.header("Filter Options")
    
    job_titles = st.sidebar.multiselect(
        "Select Job Titles",
        options=df['Normalized_Job_Title'].unique(),
        default=df['Normalized_Job_Title'].unique()
    )
    
    exp_levels = st.sidebar.multiselect(
        "Select Experience Level",
        options=df['Experience_Level'].unique(),
        default=df['Experience_Level'].unique()
    )

    col_min, col_max = st.sidebar.columns(2)
    with col_min:
        min_salary = st.number_input("Minimum Salary (INR)", min_value=0, max_value=int(df['Salary'].max()), value=int(df['Salary'].min()), step=100000)
    with col_max:
        max_salary = st.number_input("Maximum Salary (INR)", min_value=0, max_value=int(df['Salary'].max()), value=int(df['Salary'].max()), step=100000)

    # Apply filters to the DataFrame
    filtered_df = df[
        (df['Normalized_Job_Title'].isin(job_titles)) &
        (df['Experience_Level'].isin(exp_levels)) &
        (df['Salary'] >= min_salary) &
        (df['Salary'] <= max_salary) 
    ]

    if filtered_df.empty:
        st.error("No data matches the selected filters. Please adjust your selections.")
    else:
        
        # --- NEW CHART: ---
        st.header("Overall Job Demand Volume")
        
        total_job_counts = filtered_df['Normalized_Job_Title'].value_counts().nlargest(5).reset_index()
        total_job_counts.columns = ['Job Title', 'Total Postings']

        fig_overall_jobs = px.bar(total_job_counts, x='Total Postings', y='Job Title', orientation='h',
                               title='Top Job Titles by Total Postings (Filtered View)',
                               template=TEMPLATE, 
                               color_discrete_sequence=COLOR_PALETTE)
        fig_overall_jobs.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_overall_jobs, use_container_width=True)


        # --- TREND ANALYSIS ---
        st.header("Job Demand and Salary Trends (Continuous)")

        # Chart 1: Job Postings Trend Over Time by Title (Date-to-Date)
        st.subheader(" Job Postings Trend by Title")
        job_counts_by_date = filtered_df.groupby(['Date', 'Normalized_Job_Title']).size().reset_index(name='Daily Postings')
        
        fig_jobs = px.line(job_counts_by_date, x='Date', y='Daily Postings', 
                           color='Normalized_Job_Title', 
                           title='Daily Job Postings by Title Trend',
                           template=TEMPLATE, 
                           color_discrete_sequence=COLOR_PALETTE)
        fig_jobs.update_layout(xaxis_title="Date of Posting", 
                               yaxis_title="Daily Job Postings",
                               hovermode="x unified")
        st.plotly_chart(fig_jobs, use_container_width=True)

        # Chart 2: Average Salary Trend Over Time by Title (Date-to-Date)
        st.subheader(" Average Salary Trend Over Time by Title (INR)")
        avg_salary_by_date = filtered_df.groupby(['Date', 'Normalized_Job_Title'])['Salary'].mean().reset_index()
        
        fig_salary_trend = px.line(avg_salary_by_date, x='Date', y='Salary', 
                                   color='Normalized_Job_Title', 
                                   title='Average Salary Trend (Date-to-Date - INR)',
                                   template=TEMPLATE, 
                                   color_discrete_sequence=COLOR_PALETTE)
        fig_salary_trend.update_layout(xaxis_title="Date of Posting", 
                                       yaxis_title="Average Salary (INR)",
                                       hovermode="x unified")
        st.plotly_chart(fig_salary_trend, use_container_width=True)

        # ------------------------------------------------------------------
        # --- TOP HIRING COMPANIES ---
        # ------------------------------------------------------------------
        st.markdown("---")
        st.header("Top Hiring Entities")

        # Chart 5: Top 10 Companies by Job Postings
        st.subheader(" Top 10 Companies Driving Demand")
        company_counts = filtered_df['Company_Name'].value_counts().nlargest(10).reset_index()
        company_counts.columns = ['Company Name', 'Job Count']
        
        fig_companies = px.bar(company_counts, x='Job Count', y='Company Name', orientation='h',
                               title='Top 10 Companies by Job Volume',
                               template=TEMPLATE, 
                               color_discrete_sequence=COLOR_PALETTE)
        fig_companies.update_layout(yaxis={'categoryorder':'total ascending'}) # Sort bars
        st.plotly_chart(fig_companies, use_container_width=True)

        # --- SKILLS AND MARKET VALUE ANALYSIS ---
        st.markdown("---")
        st.header("Skills and Market Value Analysis")
        
        col1, col2 = st.columns(2)
        
        # Prepare skills data
        all_skills = filtered_df['Required_Skills'].str.split(', ').explode().str.strip().dropna()
        top_skills = all_skills.value_counts().nlargest(10).index.tolist()

        # Chart 3: Top Demanded Skills (DONUT CHART - Proportional View)
        with col1:
            st.subheader("3. Top 10 Most Demanded Skills")
            skills_count = all_skills.value_counts().nlargest(10).reset_index()
            skills_count.columns = ['Skill', 'Count']
            
            fig_skills = px.pie(skills_count, 
                                values='Count', 
                                names='Skill', 
                                title='Distribution of Top 10 Demanded Skills',
                                template=TEMPLATE,
                                hole=0.4, # Creates the donut shape
                                color_discrete_sequence=COLOR_PALETTE)
            st.plotly_chart(fig_skills, use_container_width=True)
            
        # Chart 4: Average Salary by Skill (Bar Chart - Market Value)
        with col2:
            st.subheader("4. Average Salary by Top Skills (INR)")
            skill_salary_data = []
            for skill in top_skills:
                escaped_skill = re.escape(skill)
                skill_df = filtered_df[filtered_df['Required_Skills'].str.contains(escaped_skill, case=False, na=False)]
                
                if not skill_df.empty:
                    avg_sal = skill_df['Salary'].mean()
                    skill_salary_data.append({'Skill': skill, 'Average Salary': avg_sal})
            
            skills_df = pd.DataFrame(skill_salary_data).sort_values(by='Average Salary', ascending=True)
            # FIXED LINE: Changed color setting to match professional style
            fig_sal_skills = px.bar(skills_df, x='Average Salary', y='Skill', orientation='h', 
                                  title='Salary Impact of Top Skills (INR)',
                                  template=TEMPLATE, 
                                  color='Average Salary') # Use color for intensity
            st.plotly_chart(fig_sal_skills, use_container_width=True)