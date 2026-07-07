from __future__ import annotations
import pandas as pd
import numpy as np

def safe_dataframe(data):
    try:
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            return data

        if df.empty:
            return df

        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].map(lambda x: "" if x is None or (isinstance(x, float) and np.isnan(x)) else str(x))
        return df
    except Exception:
        try:
            return pd.DataFrame(data).astype(str)
        except Exception:
            return data

def patch_streamlit_dataframe(st):
    if getattr(st, "_maru_dataframe_patched", False):
        return
    original_dataframe = st.dataframe
    def wrapped_dataframe(data=None, *args, **kwargs):
        return original_dataframe(safe_dataframe(data), *args, **kwargs)
    st.dataframe = wrapped_dataframe
    st._maru_dataframe_patched = True
