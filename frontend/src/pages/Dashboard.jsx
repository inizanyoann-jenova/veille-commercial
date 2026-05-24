import { useState } from 'react'
import KpiGrid from '../components/KpiGrid'
import TendersTable from '../components/TendersTable'
import TenderDetail from '../components/TenderDetail'

export default function Dashboard() {
  const [status, setStatus] = useState('Tous')
  const [secteur, setSecteur] = useState('Public')
  const [searchText, setSearchText] = useState('')
  const [gonogo, setGonogo] = useState('Tous')
  const [selectedId, setSelectedId] = useState(null)

  return (
    <div className="p-6 space-y-5">
      <KpiGrid />
      <TendersTable
        status={status}
        secteur={secteur}
        searchText={searchText}
        gonogo={gonogo}
        onStatusChange={setStatus}
        onSecteurChange={setSecteur}
        onSearchChange={setSearchText}
        onGonogoChange={setGonogo}
        onRowClick={setSelectedId}
      />
      <TenderDetail tenderId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
