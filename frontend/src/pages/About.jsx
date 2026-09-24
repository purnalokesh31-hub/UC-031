import { Activity, AlertTriangle, BarChart3, FlaskConical, Leaf, ShieldCheck } from "lucide-react";
import "../about.css";

const steps = [
  {
    number: "01",
    title: "Describe the field",
    text: "Choose a crop and enter nitrogen, phosphorus, potassium, soil pH, moisture, temperature, humidity and rainfall.",
    icon: Leaf,
  },
  {
    number: "02",
    title: "Compare candidate models",
    text: "Crop-specific classical models and a simulated quantum model are tuned with four-fold cross-validation on training rows.",
    icon: FlaskConical,
  },
  {
    number: "03",
    title: "Select and estimate",
    text: "The model with the lowest cross-validation error is selected. The estimate is shown with a 90% interval calibrated on a separate set.",
    icon: Activity,
  },
];

export default function About() {
  return (
    <main className="page-content about-page">
      <header className="about-hero">
        <div className="about-hero-copy">
          <span className="about-eyebrow"><span /> MODEL METHOD</span>
          <h1>How CropGuard estimates yield</h1>
          <p>See how field inputs become a research estimate, what the model scores mean, and where those results stop applying.</p>
        </div>
        <div className="about-hero-mark" aria-hidden="true"><Leaf size={30} /></div>
        <div className="about-facts" aria-label="Model coverage">
          <span><strong>6</strong> crops</span>
          <span><strong>8</strong> field measurements</span>
          <span><strong>90%</strong> target interval</span>
          <span className="about-facts-note">Synthetic-data research preview</span>
        </div>
      </header>

      <section className="about-section" aria-labelledby="method-heading">
        <div className="about-section-heading">
          <div>
            <span className="about-kicker">THE PROCESS</span>
            <h2 id="method-heading">From field inputs to an estimate</h2>
          </div>
          <p>Each step is designed to keep the estimate traceable and expose uncertainty.</p>
        </div>
        <div className="about-steps">
          {steps.map(({ number, title, text, icon: Icon }) => (
            <article className="about-step card" key={number}>
              <div className="about-step-top">
                <span className="about-step-number">{number}</span>
                <span className="about-step-icon"><Icon size={19} /></span>
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
        <div className="about-quantum-note">
          <span className="about-quantum-icon"><FlaskConical size={17} /></span>
          <p><strong>About the quantum model</strong> It encodes the eight inputs using four simulated qubits and compares examples with an exact quantum kernel. This is a classical simulation, not a quantum computer.</p>
        </div>
      </section>

      <section className="about-section" aria-labelledby="scores-heading">
        <div className="about-section-heading">
          <div>
            <span className="about-kicker">READING THE RESULTS</span>
            <h2 id="scores-heading">What the scores tell you</h2>
          </div>
          <p>These describe performance on held-out synthetic records for the selected crop.</p>
        </div>
        <div className="about-score-grid">
          <article className="about-score-card">
            <span className="about-score-icon"><BarChart3 size={18} /></span>
            <h3>Mean absolute error</h3>
            <p>Average difference between an estimate and the recorded value, in quintals per hectare. Lower is better.</p>
          </article>
          <article className="about-score-card">
            <span className="about-score-icon"><Activity size={18} /></span>
            <h3>R²</h3>
            <p>How much variation the model explains on the evaluation set. It can be negative and is not a percent correct.</p>
          </article>
          <article className="about-score-card">
            <span className="about-score-icon"><ShieldCheck size={18} /></span>
            <h3>Prediction interval</h3>
            <p>A calibrated range intended to contain 90% of outcomes under similar data conditions. It is not a guarantee.</p>
          </article>
        </div>
      </section>

      <section className="about-limitations" aria-labelledby="limits-heading">
        <div className="about-limits-icon"><AlertTriangle size={20} /></div>
        <div className="about-limits-copy">
          <span className="about-kicker">IMPORTANT LIMITS</span>
          <h2 id="limits-heading">Research estimates, not field-validated advice</h2>
          <p>The yield dataset contains 3,000 synthetic rows, 500 per crop, and no independent farm, season or harvest measurements. These test scores do not establish accuracy on real farms. Inputs outside the training range are flagged and calibrated intervals are withheld.</p>
          <p>Disease scanning uses a separate pretrained image classifier. Yield model training does not validate or improve the disease model.</p>
        </div>
        <div className="about-data-mark" aria-hidden="true"><BarChart3 size={22} /></div>
      </section>

      <div className="about-footer-note">
        <span><ShieldCheck size={15} /></span>
        <p>For research and demonstration only. Do not use a yield estimate alone to make planting, financial, fertilizer or treatment decisions.</p>
      </div>
    </main>
  );
}
