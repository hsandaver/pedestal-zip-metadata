"""Local Streamlit interface for uploading ZIPs and downloading metadata reports."""
import pandas as pd
import streamlit as st
from pedestal import process
from exports import export_files, acquia_rows, SCHEMAS, ACQUIA_FIELDS, EXPORT_NAMES, csv_bytes

st.set_page_config(page_title='Pedestal metadata', layout='wide')
st.title('Pedestal metadata')
st.write('Upload Pedestal3D object ZIPs to extract catalogue metadata and check model dependencies.')
st.caption('Download Acquia DAM metadata using the 11 columns in your supplied ABP workbook.')

archives = st.file_uploader('Upload object ZIPs', type=['zip'], accept_multiple_files=True, key='archives')
st.caption('Your original files stay unchanged. Results download through your browser; no folder path is needed.')

if st.button('Process ZIPs', key='process', type='primary'):
    st.session_state.pop('result', None)
    st.session_state.pop('exports', None)
    if not archives:
        st.error('Upload at least one object ZIP to continue.')
    else:
        with st.spinner('Reading metadata and model dependencies...'):
            result = process([(item.name, item.getvalue()) for item in archives])
            st.session_state['result'] = result
            st.session_state['exports'] = export_files(result)
            st.session_state['processed_names'] = [item.name for item in archives]

if 'result' in st.session_state:
    result = st.session_state['result']
    cached_exports = st.session_state.get('exports', {})
    if (set(cached_exports) != EXPORT_NAMES
            or not cached_exports.get('acquia_dam_metadata.csv', b'').startswith(csv_bytes([], ACQUIA_FIELDS))):
        st.session_state['exports'] = export_files(result)
    files = st.session_state['exports']
    st.subheader('Results')
    names = st.session_state.get('processed_names') or list(dict.fromkeys(
        row['source_name'] for key in result for row in result[key]))
    st.caption('Results for: ' + ', '.join(names))
    columns = st.columns(4)
    for column, key, label in zip(columns, ('catalogue', 'variants', 'manifest', 'issues'),
                                  ('Object records', 'Model variants', 'Files', 'Issues')):
        column.metric(label, len(result[key]))
    if not result['catalogue']:
        st.warning('No object metadata was recognized. Download the reports and review the issues.')
    elif result['issues']:
        st.warning('Review the issues before using these records. Flagged models and duplicate records remain in the reports.')
    else:
        st.success('Reports are ready to download.')

    st.download_button('Download Acquia DAM CSV', data=files['acquia_dam_metadata.csv'],
                       file_name='acquia_dam_metadata.csv', mime='text/csv',
                       key='download_acquia_dam_metadata.csv', type='primary')
    st.caption('Uses the supplied column order, with the filename column named Filename. Missing metadata stays blank. Review issues before importing.')
    st.download_button('Download all reports (.zip)', data=files['output.zip'],
                       file_name='pedestal_metadata_reports.zip', mime='application/zip',
                       key='download_output.zip')
    st.caption('Includes the Acquia DAM CSV, four supporting CSV reports, and original metadata in JSON. Model and texture files are not included.')
    with st.expander('Download individual reports'):
        for name, data in files.items():
            if name in {'output.zip', 'acquia_dam_metadata.csv'}:
                continue
            mime = 'application/json' if name.endswith('.json') else 'text/csv'
            st.download_button('Download ' + name, data=data, file_name=name,
                               mime=mime, key='download_' + name)
        st.caption('CSV cells include spreadsheet formula protection. JSON preserves exact metadata values and original metadata bytes as base64.')

    tabs = st.tabs(['Acquia DAM', 'Catalogue', 'Model variants', 'File inventory', 'Issues'])
    with tabs[0]:
        st.dataframe(pd.DataFrame(acquia_rows(result)).reindex(columns=list(ACQUIA_FIELDS)),
                     hide_index=True, width='stretch')
    for tab, key in zip(tabs[1:], ('catalogue', 'variants', 'manifest', 'issues')):
        with tab:
            st.dataframe(pd.DataFrame(result[key]).reindex(columns=SCHEMAS[key]),
                         hide_index=True, width='stretch')
