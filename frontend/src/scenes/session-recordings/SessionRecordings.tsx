import { PageHeader } from 'lib/components/PageHeader'
import { teamLogic } from 'scenes/teamLogic'
import { useValues } from 'kea'
import { urls } from 'scenes/urls'
import { SceneExport } from 'scenes/sceneTypes'
import { sessionRecordingsListLogic } from 'scenes/session-recordings/playlist/sessionRecordingsListLogic'
import { SessionRecordingsPlaylist } from './playlist/SessionRecordingsPlaylist'
import { AlertMessage } from 'lib/components/AlertMessage'
import { LemonButton, Link } from '@posthog/lemon-ui'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { FEATURE_FLAGS } from 'lib/constants'
import { Tabs } from 'antd'
import { SessionRecordingsTabs } from '~/types'
import { SavedSessionRecordingPlaylists } from './saved-playlists/SavedSessionRecordingPlaylists'
import { Tooltip } from 'lib/components/Tooltip'
import { router } from 'kea-router'
import { sessionRecordingsLogic } from './sessionRecordingsLogic'
import { Spinner } from 'lib/components/Spinner/Spinner'

export function SessionsRecordings(): JSX.Element {
    const { currentTeam } = useValues(teamLogic)
    const { featureFlags } = useValues(featureFlagLogic)
    const { tab } = useValues(sessionRecordingsLogic)
    const showRecordingPlaylists = !!featureFlags[FEATURE_FLAGS.RECORDING_PLAYLISTS]
    const logic = sessionRecordingsListLogic({ key: 'recents' })

    const { filterQueryParams } = useValues(logic)

    const recentRecordings = (
        <>
            <SessionRecordingsPlaylist key="recents" />
        </>
    )

    return (
        <div>
            <PageHeader
                title={<div>Session Recordings</div>}
                buttons={
                    tab === SessionRecordingsTabs.Recent ? (
                        <>
                            <Tooltip title="Save the currently filters as a dynamic playlist" placement="left">
                                <LemonButton
                                    type="primary"
                                    onClick={() =>
                                        router.actions.push(urls.sessionRecordingPlaylist('new', filterQueryParams))
                                    }
                                >
                                    Save as playlist
                                </LemonButton>
                            </Tooltip>
                        </>
                    ) : undefined
                }
            />
            {showRecordingPlaylists && (
                <Tabs
                    activeKey={tab}
                    style={{ borderColor: '#D9D9D9' }}
                    onChange={(t) => router.actions.push(urls.sessionRecordings(t as SessionRecordingsTabs))}
                >
                    <Tabs.TabPane tab="Recent" key={SessionRecordingsTabs.Recent} />
                    <Tabs.TabPane tab="All Playlists" key={SessionRecordingsTabs.All} />
                    <Tabs.TabPane tab="Your Playlists" key={SessionRecordingsTabs.Yours} />
                    <Tabs.TabPane tab="Pinned" key={SessionRecordingsTabs.Pinned} />
                    <Tabs.TabPane tab="History" key={SessionRecordingsTabs.History} />
                </Tabs>
            )}
            {currentTeam && !currentTeam?.session_recording_opt_in ? (
                <div className="mb-4">
                    <AlertMessage type="info">
                        Session recordings are currently disabled for this project. To use this feature, please go to
                        your <Link to={`${urls.projectSettings()}#recordings`}>project settings</Link> and enable it.
                    </AlertMessage>
                </div>
            ) : null}
            {showRecordingPlaylists ? (
                !tab ? (
                    <Spinner />
                ) : tab === SessionRecordingsTabs.Recent ? (
                    recentRecordings
                ) : tab === SessionRecordingsTabs.History ? (
                    <p>WIP</p>
                ) : (
                    <SavedSessionRecordingPlaylists tab={tab} />
                )
            ) : (
                recentRecordings
            )}
        </div>
    )
}

export const scene: SceneExport = {
    component: SessionsRecordings,
    logic: sessionRecordingsLogic,
}
