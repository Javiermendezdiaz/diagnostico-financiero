/**
 * DATA RIGHTS PAGE — Integration Example
 *
 * Shows how to integrate ConsentManager into a full page
 * within UserProfile or as standalone Settings > Data & Privacy
 */

import React from 'react';
import { ConsentManager } from '@/components/DataRights/ConsentManager';
import styles from './DataRightsPage.module.css';

export const DataRightsPage: React.FC = () => {
  return (
    <div className={styles.page}>
      {/* Header Section */}
      <div className={styles.pageHeader}>
        <h1>Privacidad y datos</h1>
        <p className={styles.pageSubtitle}>
          Controla tus datos personales, consentimientos y solicitudes de derechos GDPR
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className={styles.tabsContainer}>
        <nav className={styles.tabs}>
          <button className={`${styles.tab} ${styles.tabActive}`}>
            Consentimientos
          </button>
          <button className={styles.tab}>
            Solicitudes de datos
          </button>
          <button className={styles.tab}>
            Configuración de privacidad
          </button>
        </nav>
      </div>

      {/* Content Area */}
      <div className={styles.pageContent}>
        {/* Consent Manager */}
        <section className={styles.section}>
          <ConsentManager />
        </section>

        {/* Additional Sections (Future Tasks #34+) */}
        <section className={styles.section} style={{ marginTop: '3rem', opacity: 0.5 }}>
          <h2>Solicitudes de acceso a datos</h2>
          <p>Coming in Task #34 — Request data export, deletion, portability</p>
        </section>

        <section className={styles.section} style={{ marginTop: '3rem', opacity: 0.5 }}>
          <h2>Configuración de privacidad</h2>
          <p>Coming in Task #35 — Third-party sharing, analytics opt-out</p>
        </section>
      </div>

      {/* Footer */}
      <div className={styles.pageFooter}>
        <p className={styles.footerText}>
          Para más información sobre tus derechos GDPR, consulta nuestra{' '}
          <a href="/privacy" className={styles.link}>
            Política de Privacidad
          </a>
          .
        </p>
      </div>
    </div>
  );
};

/**
 * USAGE IN APP
 *
 * Add to your routing:
 *
 * <Route path="/account/privacy" element={<DataRightsPage />} />
 *
 * Or embed in UserProfile tabs:
 *
 * <UserProfile>
 *   <TabPanel label="Consentimientos">
 *     <ConsentManager />
 *   </TabPanel>
 * </UserProfile>
 */
