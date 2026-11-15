# AI-Based Urban Flood Digital Twin With Predictive Climate Analysis

Open the dashboard and use **Project modules** on the overview page to walk through the five sections.

| Module | Show this in the demo |
| --- | --- |
| Data Collection and Preprocessing | Open **Rainfall data** and **Flood evidence**. Show the June 2026 city reports and explain that their exact incident locations and times still need verification. |
| AI-Based Prediction | Open **Run rainfall estimate** and click **Run demo example** to run the saved model with example inputs. Then open **Model evaluation**. Show the Random Forest rainfall evaluation alongside the baselines. Explain that the zero-rainfall baseline had lower mean absolute error in the reported periods. |
| GIS Mapping | Open **GIS Explorer**, click inside Ballari, and inspect the terrain and drainage values for that location. |
| Digital Twin and Simulation | Open **Rainfall Scenarios**. Compare 50 mm and 100 mm over 2 hours with the same runoff fraction of 0.5 in both scenarios. The estimated runoff volume doubles under the formula. Then open **Spatial Scenario** to show how the dashboard displays estimated upstream runoff volume. |
| Explainable AI and Decision Support | Open **Model explanation**. Show the rainfall model's global feature importance and explain what it says about that model's inputs. |

The current release implements a research prototype for Ballari. Flood occurrence and severity prediction, calibrated inundation and depth, and SHAP explanations of a trained flood model remain pending. The scenario comparison illustrates the effect of its input assumptions.
