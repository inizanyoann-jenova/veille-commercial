import { useState } from 'react'
import KpiGrid from '../components/KpiGrid'
import TendersTable from '../components/TendersTable'

export default function Dashboard() {
  const [status, setStatus] = useState('Tous')
  const [secteur, setSecteur] = useState('Public')
  const [searchText, setSearchText] = useState('')

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
      />
    </div>
  )
}
