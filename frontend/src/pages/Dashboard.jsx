import { useState } from 'react'
import KpiGrid from '../components/KpiGrid'
import TendersTable from '../components/TendersTable'
import TenderDetail from '../components/TenderDetail'

export default function Dashboard() {
  const [status, setStatus] = useState('Tous')
  const [secteur, setSecteur] = useState('Public')
  const [searchText, setSearchText] = useState('')
  const [selectedId, setSelectedId] = useState(null)

  return (
    <div className="p-5 space-y-5">
      <KpiGrid />
      <TendersTable
        status={status}
        secteur={secteur}
        searchText={searchText}
        onStatusChange={setStatus}
        onSecteurChange={setSecteur}
        onSearchChange={setSearchText}
        onRowClick={setSelectedId}
      />
      <TenderDetail tenderId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
