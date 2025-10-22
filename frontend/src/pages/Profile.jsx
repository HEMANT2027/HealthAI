import { useMemo, useState } from 'react'

function Section({ title, children, right }) {
  return (
    <section className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-900">{title}</h3>
        {right}
      </div>
      <div className="mt-4">
        {children}
      </div>
    </section>
  )
}

function Pill({ children }) {
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-vibrant-blue border border-blue-100">
      {children}
    </span>
  )
}

function Profile() {
  // Mocked example shaped by the schema from output.py
  const sample = useMemo(() => ({
    pseudonym_id: 'P-1A2B-3C4D',
    patient_summary: 'Middle-aged patient with knee osteoarthritis planning for minimally invasive knee replacement. Vitals stable. No known allergies. Good rehab potential.',
    created_at: new Date('2025-01-05T09:00:00Z'),
    updated_at: new Date('2025-10-15T10:00:00Z'),
    itinerary: {
      days: [
        { day: 1, plan: 'Arrival and pre-op consultation', location: 'City Hospital', notes: 'Fasting after midnight' },
        { day: 2, plan: 'Surgery and post-op monitoring', location: 'City Hospital', notes: 'Physio introduction in evening' },
        { day: 3, plan: 'Physiotherapy and discharge', location: 'City Hospital', notes: 'Arrange hotel transfer' },
        { day: 4, plan: 'Light city tour (wheelchair accessible)', location: 'Museum District', notes: 'Avoid stairs' },
      ]
    },
    hospital_suggestions: [
      { name: 'Global Ortho Care', city: 'Bengaluru, IN', rating: 4.7, accreditation: 'JCI', est_cost_usd: 8200 },
      { name: 'Bangkok Ortho Center', city: 'Bangkok, TH', rating: 4.6, accreditation: 'JCI', est_cost_usd: 7900 },
      { name: 'Istanbul Joint Institute', city: 'Istanbul, TR', rating: 4.5, accreditation: 'JCI', est_cost_usd: 7600 },
    ],
    visits: [
      {
        visit_timestamp: new Date('2025-01-05T09:00:00Z'),
        visit_type: 'initial',
        chief_complaint: 'Chronic right knee pain and reduced mobility',
        status: 'completed',
        human_review_completed: true,
        ingests: [
          { ingest_id: 'ING-001', type: 'imaging', original_filename: 'knee_xray.png', upload_timestamp: new Date('2025-01-05T09:10:00Z'), processing_status: 'completed', content_type: 'image/png', file_size: 154322 },
          { ingest_id: 'ING-002', type: 'lab_report', original_filename: 'bloodwork.pdf', upload_timestamp: new Date('2025-01-05T09:12:00Z'), processing_status: 'completed', content_type: 'application/pdf', file_size: 80212 },
        ],
        outputs: {
          ner_entities: [
            { type: 'Condition', value: 'Osteoarthritis' },
            { type: 'Anatomy', value: 'Right Knee' },
          ],
          imaging_findings: [
            'Joint space narrowing in medial compartment',
            'Mild osteophyte formation',
          ],
          referral_suggestions: [
            'Orthopedic surgeon consult',
            'Physiotherapy evaluation',
          ]
        },
        visit_summary: 'Patient presents with progressive knee pain impacting ADLs. Imaging consistent with OA. Candidate for minimally invasive knee replacement pending labs.',
        doctor_notes: 'Proceed with pre-op clearance. Consider partial knee replacement based on MRI.',
        clinician_id: 'DR-ORTHO-11'
      },
      {
        visit_timestamp: new Date('2025-02-01T10:00:00Z'),
        visit_type: 'follow_up',
        chief_complaint: 'Pre-op planning and consent discussion',
        status: 'completed',
        human_review_completed: true,
        ingests: [
          { ingest_id: 'ING-010', type: 'clinical_notes', original_filename: 'preop_notes.txt', upload_timestamp: new Date('2025-02-01T10:15:00Z'), processing_status: 'completed', content_type: 'text/plain', file_size: 2048 },
        ],
        outputs: { ner_entities: [], imaging_findings: [], referral_suggestions: [] },
        visit_summary: 'Patient cleared for surgery; consent obtained. Scheduled in two weeks.',
        doctor_notes: 'Ensure physio booked for day 2 evening session.',
        clinician_id: 'DR-ORTHO-11'
      }
    ]
  }), [])

  const [expandedIndex, setExpandedIndex] = useState(0)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-gray-900">Your Profile</h1>
          <p className="mt-2 text-gray-600">Pseudonym ID: <span className="font-semibold">{sample.pseudonym_id}</span></p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Section title="Patient Summary">
              <p className="text-gray-700 leading-relaxed">{sample.patient_summary}</p>
              <div className="mt-3 text-sm text-gray-500">Updated {sample.updated_at.toLocaleString()}</div>
            </Section>

            <Section
              title="Visits Timeline"
              right={<Pill>{sample.visits.length} visits</Pill>}
            >
              <div className="space-y-4">
                {sample.visits.map((visit, index) => (
                  <div key={index} className="border border-gray-200 rounded-xl overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(expandedIndex === index ? -1 : index)}
                      className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-semibold text-gray-900">{visit.visit_type.replace('_', ' ')} • {visit.status}</p>
                        <p className="text-sm text-gray-600">{visit.visit_timestamp.toLocaleString()} — {visit.chief_complaint}</p>
                      </div>
                      <span className="text-sm text-gray-500">{expandedIndex === index ? 'Hide' : 'View'}</span>
                    </button>
                    {expandedIndex === index && (
                      <div className="p-4 grid md:grid-cols-2 gap-6">
                        <div className="space-y-3">
                          <p className="text-sm text-gray-500 font-semibold">Ingested files</p>
                          <ul className="space-y-2">
                            {visit.ingests.map(file => (
                              <li key={file.ingest_id} className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
                                <div className="min-w-0">
                                  <p className="truncate text-gray-900 font-medium">{file.original_filename}</p>
                                  <p className="text-xs text-gray-500">{file.type} • {file.content_type} • {(file.file_size/1024).toFixed(1)} KB</p>
                                </div>
                                <Pill>{file.processing_status}</Pill>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="space-y-3">
                          <p className="text-sm text-gray-500 font-semibold">AI outputs</p>
                          <div className="rounded-lg border border-gray-200 p-3">
                            <p className="text-sm font-semibold text-gray-900">Entities</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {(visit.outputs.ner_entities || []).map((e, i) => (
                                <Pill key={i}>{e.type}: {e.value}</Pill>
                              ))}
                              {(!visit.outputs.ner_entities || visit.outputs.ner_entities.length === 0) && (
                                <p className="text-sm text-gray-500">No entities</p>
                              )}
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-200 p-3">
                            <p className="text-sm font-semibold text-gray-900">Imaging findings</p>
                            <ul className="mt-2 list-disc list-inside text-sm text-gray-700 space-y-1">
                              {(visit.outputs.imaging_findings || []).map((f, i) => <li key={i}>{f}</li>)}
                              {(!visit.outputs.imaging_findings || visit.outputs.imaging_findings.length === 0) && (
                                <li className="text-gray-500">No findings</li>
                              )}
                            </ul>
                          </div>
                          <div className="rounded-lg border border-gray-200 p-3">
                            <p className="text-sm font-semibold text-gray-900">Referral suggestions</p>
                            <ul className="mt-2 list-disc list-inside text-sm text-gray-700 space-y-1">
                              {(visit.outputs.referral_suggestions || []).map((f, i) => <li key={i}>{f}</li>)}
                              {(!visit.outputs.referral_suggestions || visit.outputs.referral_suggestions.length === 0) && (
                                <li className="text-gray-500">No suggestions</li>
                              )}
                            </ul>
                          </div>
                        </div>

                        <div className="md:col-span-2 grid md:grid-cols-2 gap-4">
                          <div className="rounded-lg border border-gray-200 p-4">
                            <p className="text-sm font-semibold text-gray-900">Visit summary</p>
                            <p className="mt-1 text-sm text-gray-700">{visit.visit_summary || '—'}</p>
                          </div>
                          <div className="rounded-lg border border-gray-200 p-4">
                            <p className="text-sm font-semibold text-gray-900">Doctor notes</p>
                            <p className="mt-1 text-sm text-gray-700">{visit.doctor_notes || '—'}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          </div>

          <div className="space-y-6">
            <Section title="Itinerary">
              <ol className="space-y-3">
                {sample.itinerary.days.map(d => (
                  <li key={d.day} className="rounded-lg border border-gray-200 p-4 bg-white">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-gray-900">Day {d.day}: {d.plan}</p>
                      <Pill>{d.location}</Pill>
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{d.notes}</p>
                  </li>
                ))}
              </ol>
            </Section>

            <Section title="Hospital suggestions" right={<Pill>{sample.hospital_suggestions.length} options</Pill>}>
              <ul className="space-y-3">
                {sample.hospital_suggestions.map((h, i) => (
                  <li key={i} className="rounded-lg border border-gray-200 p-4 bg-white">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div>
                        <p className="font-semibold text-gray-900">{h.name}</p>
                        <p className="text-sm text-gray-600">{h.city} • {h.accreditation}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Pill>{h.rating.toFixed(1)}★</Pill>
                        <Pill>${h.est_cost_usd.toLocaleString()}</Pill>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Profile