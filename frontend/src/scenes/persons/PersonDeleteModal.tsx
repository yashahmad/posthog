import { useActions, useValues } from 'kea'
import { personsLogic } from './personsLogic'
import { asDisplay } from './PersonHeader'
import { LemonButton, LemonModal } from '@posthog/lemon-ui'
import { PersonType } from '~/types'

export function PersonDeleteModal(): JSX.Element | null {
    const { personDeleteModal } = useValues(personsLogic)
    const { deletePerson, showPersonDeleteModal } = useActions(personsLogic)

    return (
        <LemonModal
            isOpen={!!personDeleteModal}
            onClose={() => showPersonDeleteModal(null)}
            title={`Are you sure you want to delete "${asDisplay(personDeleteModal)}"?`}
            description={
                <>
                    <p>This action cannot be undone.</p>
                    <p>
                        If you want to re-use the distinct ids do NOT use delete person and instead use split IDs.
                        Re-using deleted person's distinct ids is not supported and will result in bad data state.
                    </p>
                    <p>
                        If you opt to delete the person and its corresponding events, the events will not be immediately
                        removed. Instead these events will be deleted on a set schedule during non-peak usage times.
                        <a
                            href="https://posthog.com/docs/privacy/data-deletion"
                            target="_blank"
                            rel="noopener"
                            className="font-bold"
                        >
                            {' '}
                            Learn more
                        </a>
                    </p>
                </>
            }
            footer={
                <>
                    <LemonButton
                        status="danger"
                        type="secondary"
                        onClick={() => {
                            deletePerson({ person: personDeleteModal as PersonType, deleteEvents: true })
                            showPersonDeleteModal(null)
                        }}
                        data-attr="delete-person-with-events"
                    >
                        Delete person and all corresponding events
                    </LemonButton>
                    <LemonButton
                        type="secondary"
                        onClick={() => showPersonDeleteModal(null)}
                        data-attr="delete-person-cancel"
                    >
                        Cancel
                    </LemonButton>
                    <LemonButton
                        type="primary"
                        status="danger"
                        onClick={() => {
                            deletePerson({ person: personDeleteModal as PersonType, deleteEvents: false })
                            showPersonDeleteModal(null)
                        }}
                        data-attr="delete-person-no-events"
                    >
                        Delete person
                    </LemonButton>
                </>
            }
        />
    )
}
