"""
XAI Dashboard - Interactive Web UI
Streamlit-based interface for ransomware detection with explanations
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
import tempfile
import shutil

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from feature_extraction import PEFeatureExtractor
from xai_explainer import RansomwareExplainer

# Page config
st.set_page_config(
    page_title="Ransomware XAI Analyzer",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .malware-box {
        background-color: #ffebee;
        border-left: 5px solid #c62828;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .benign-box {
        background-color: #e8f5e9;
        border-left: 5px solid #2e7d32;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'explainer' not in st.session_state:
    st.session_state.explainer = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Model selection
    model_path = st.text_input(
        "Model Path",
        value="ransomware_lgbm_1M_final.txt",
        help="Path to trained LightGBM model"
    )
    
    # Load model button
    if st.button("🔄 Load Model"):
        try:
            with st.spinner("Loading model..."):
                st.session_state.explainer = RansomwareExplainer(model_path)
            st.success("✅ Model loaded successfully!")
        except Exception as e:
            st.error(f"❌ Error loading model: {e}")
    
    st.divider()
    
    # Threshold
    threshold = st.slider(
        "Detection Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="Probability threshold for malware classification"
    )
    
    if st.session_state.explainer:
        st.session_state.explainer.threshold = threshold
    
    st.divider()
    
    # History
    st.subheader("📊 Analysis History")
    if st.session_state.analysis_results:
        for i, result in enumerate(st.session_state.analysis_results[-5:]):
            emoji = "🦠" if result['prediction'] == "MALWARE" else "✅"
            st.text(f"{emoji} {result['file'][:20]}...")
    else:
        st.info("No analysis yet")
    
    if st.button("🗑️ Clear History"):
        st.session_state.analysis_results = []
        st.rerun()

# Main content
st.title("🛡️ Ransomware Detection with Explainable AI")
st.markdown("Upload PE files for analysis with detailed explanations")

# Check if model is loaded
if st.session_state.explainer is None:
    st.warning("⚠️ Please load a model first (see sidebar)")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📂 Single File Analysis", "📦 Batch Analysis", "📊 Statistics"])

# TAB 1: Single File Analysis
with tab1:
    st.header("Upload PE File for Analysis")
    
    uploaded_file = st.file_uploader(
        "Choose a PE file (.exe, .dll, .sys)",
        type=['exe', 'dll', 'sys'],
        help="Upload a Windows executable file for analysis"
    )
    
    if uploaded_file:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📄 File Information")
            file_size = Path(tmp_path).stat().st_size
            st.metric("File Name", uploaded_file.name)
            st.metric("File Size", f"{file_size:,} bytes")
        
        # Analyze button
        if st.button("🔍 Analyze File", type="primary"):
            with st.spinner("Analyzing file... This may take a few seconds."):
                try:
                    # Get explanation
                    result = st.session_state.explainer.explain_file(tmp_path, top_n=15)
                    
                    if result['success']:
                        # Save to history
                        result['file'] = uploaded_file.name
                        st.session_state.analysis_results.append(result)
                        
                        # Display results
                        st.divider()
                        
                        # Prediction box
                        prob = result['probability']
                        pred = result['prediction']
                        
                        if pred == "MALWARE":
                            st.markdown(f"""
                            <div class="malware-box">
                                <h2>🦠 MALWARE DETECTED</h2>
                                <h3>Confidence: {prob:.1%}</h3>
                                <p>This file exhibits malicious characteristics and should be treated with caution.</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="benign-box">
                                <h2>✅ BENIGN FILE</h2>
                                <h3>Confidence: {(1-prob):.1%}</h3>
                                <p>This file appears to be safe based on our analysis.</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Malware Score",
                                f"{prob:.3f}",
                                delta=f"{(prob - 0.5):.3f}" if prob != 0.5 else None
                            )
                        with col2:
                            st.metric(
                                "Push to Malware",
                                f"{result['malware_contribution']:+.4f}"
                            )
                        with col3:
                            st.metric(
                                "Push to Benign",
                                f"{result['benign_contribution']:+.4f}"
                            )
                        
                        # Top features
                        st.subheader("🎯 Top Contributing Features")
                        
                        # Create DataFrame
                        df_explanations = pd.DataFrame(result['top_explanations'])
                        
                        # Bar chart
                        fig = go.Figure()
                        
                        colors = ['#c62828' if x > 0 else '#2e7d32' for x in df_explanations['shap_value']]
                        
                        fig.add_trace(go.Bar(
                            x=df_explanations['shap_value'],
                            y=df_explanations['feature_name'],
                            orientation='h',
                            marker_color=colors,
                            text=df_explanations['contribution_pct'].apply(lambda x: f"{x:.1f}%"),
                            textposition='outside'
                        ))
                        
                        fig.update_layout(
                            title="SHAP Feature Contributions",
                            xaxis_title="SHAP Value",
                            yaxis_title="Feature",
                            height=500,
                            yaxis={'categoryorder': 'total ascending'}
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Detailed table
                        st.subheader("📋 Detailed Feature Analysis")
                        
                        # Format table
                        df_display = df_explanations.copy()
                        df_display['shap_value'] = df_display['shap_value'].apply(lambda x: f"{x:+.4f}")
                        df_display['feature_value'] = df_display['feature_value'].apply(lambda x: f"{x:.4f}")
                        df_display['contribution_pct'] = df_display['contribution_pct'].apply(lambda x: f"{x:.1f}%")
                        
                        st.dataframe(
                            df_display[['rank', 'feature_name', 'feature_value', 'shap_value', 'contribution_pct']],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Download report
                        st.divider()
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("📥 Download HTML Report"):
                                report_path = f"{Path(tmp_path).stem}_report.html"
                                st.session_state.explainer.generate_report(tmp_path, report_path)
                                
                                with open(report_path, 'r', encoding='utf-8') as f:
                                    st.download_button(
                                        "⬇️ Download Report",
                                        f.read(),
                                        file_name=f"{uploaded_file.name}_report.html",
                                        mime="text/html"
                                    )
                        
                    else:
                        st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    st.error(f"❌ Error during analysis: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Cleanup temp file
        try:
            Path(tmp_path).unlink()
        except:
            pass

# TAB 2: Batch Analysis
with tab2:
    st.header("Batch File Analysis")
    st.info("Upload multiple PE files for comparison")
    
    uploaded_files = st.file_uploader(
        "Choose multiple PE files",
        type=['exe', 'dll', 'sys'],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("🔍 Analyze All Files", type="primary"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Analyzing {uploaded_file.name}...")
            
            # Save to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name
            
            try:
                result = st.session_state.explainer.explain_file(tmp_path, top_n=5)
                if result['success']:
                    results.append({
                        'File': uploaded_file.name,
                        'Prediction': result['prediction'],
                        'Confidence': f"{result['probability']:.2%}",
                        'Malware Push': f"{result['malware_contribution']:+.4f}",
                        'Benign Push': f"{result['benign_contribution']:+.4f}"
                    })
            except:
                results.append({
                    'File': uploaded_file.name,
                    'Prediction': 'ERROR',
                    'Confidence': 'N/A',
                    'Malware Push': 'N/A',
                    'Benign Push': 'N/A'
                })
            
            # Cleanup
            try:
                Path(tmp_path).unlink()
            except:
                pass
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("✅ Analysis complete!")
        
        # Display results table
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True)
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", len(results))
        with col2:
            malware_count = sum(1 for r in results if r['Prediction'] == 'MALWARE')
            st.metric("Malware Detected", malware_count)
        with col3:
            benign_count = sum(1 for r in results if r['Prediction'] == 'BENIGN')
            st.metric("Benign Files", benign_count)

# TAB 3: Statistics
with tab3:
    st.header("Analysis Statistics")
    
    if st.session_state.analysis_results:
        # Create DataFrame
        df_history = pd.DataFrame([
            {
                'File': r['file'],
                'Prediction': r['prediction'],
                'Probability': r['probability']
            }
            for r in st.session_state.analysis_results
        ])
        
        # Pie chart
        pred_counts = df_history['Prediction'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=pred_counts.index,
            values=pred_counts.values,
            marker_colors=['#c62828' if x == 'MALWARE' else '#2e7d32' for x in pred_counts.index]
        )])
        
        fig.update_layout(title="Prediction Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Histogram
        fig = px.histogram(
            df_history,
            x='Probability',
            color='Prediction',
            nbins=20,
            title="Confidence Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Full history
        st.subheader("Complete Analysis History")
        st.dataframe(df_history, use_container_width=True)
        
    else:
        st.info("No analysis history available. Start analyzing files!")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🛡️ Ransomware Detection Tool with Explainable AI</p>
    <p>Powered by LightGBM + SHAP</p>
</div>
""", unsafe_allow_html=True)