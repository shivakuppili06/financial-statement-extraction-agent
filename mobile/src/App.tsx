import React, { useState } from 'react';
import {
  IonApp,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonContent,
  IonCard,
  IonCardHeader,
  IonCardTitle,
  IonCardContent,
  IonButton,
  IonIcon,
  IonItem,
  IonLabel,
  IonBadge,
  IonSpinner,
  setupIonicReact
} from '@ionic/react';

/* Core Ionic CSS required for components to work properly */
import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';

setupIonicReact();

export const App: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5200/api/FinancialAnalysis/analyze', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setResult(data);
    } catch (err) {
      // Fallback directly to Python microservice if gateway unavailable
      try {
        const response = await fetch('http://localhost:5000/api/analyze', {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();
        setResult(data);
      } catch (error) {
        alert('Upload failed. Ensure backend services are running.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <IonApp>
      <IonHeader>
        <IonToolbar color="primary">
          <IonTitle>FinExtract Mobile Audit</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent className="ion-padding">
        <IonCard>
          <IonCardHeader>
            <IonCardTitle>Mobile Document Upload</IonCardTitle>
          </IonCardHeader>
          <IonCardContent>
            <p>Upload a financial PDF balance sheet or Excel workbook for instant AI extraction & math sanity audit.</p>
            <br />
            <input type="file" accept=".pdf,.xlsx,.xls" onChange={handleFileChange} />
            <br /><br />
            <IonButton expand="full" onClick={handleUpload} disabled={!file || loading}>
              {loading ? <IonSpinner name="crescent" /> : 'Audit Statement'}
            </IonButton>
          </IonCardContent>
        </IonCard>

        {result && (
          <IonCard>
            <IonCardHeader>
              <IonCardTitle>
                Audit Results{' '}
                <IonBadge color={result.risk_assessment?.level === 'HIGH' ? 'danger' : 'success'}>
                  {result.risk_assessment?.level || 'Passed'}
                </IonBadge>
              </IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              {result.guardrail_alerts && result.guardrail_alerts.length > 0 && (
                <div style={{ color: 'red', marginBottom: '10px' }}>
                  <strong>Guardrail Alerts:</strong>
                  <ul>
                    {result.guardrail_alerts.map((alert: any, idx: number) => (
                      <li key={idx}>{alert.message || alert}</li>
                    ))}
                  </ul>
                </div>
              )}
              <pre style={{ background: '#f4f4f4', padding: '10px', borderRadius: '5px', overflowX: 'auto' }}>
                {JSON.stringify(result.extraction, null, 2)}
              </pre>
            </IonCardContent>
          </IonCard>
        )}
      </IonContent>
    </IonApp>
  );
};

export default App;
